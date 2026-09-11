"""SRT subtitle parser, validator, and serializer utilities.

This module provides helper data structures and functions to parse SRT files,
batch subtitle entries for LLM processing, and serialize translated subtitles
while maintaining original timestamps and formatting.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class SubtitleEntry:
    """Represents a single subtitle block in an SRT file.

    Attributes:
        index: The 1-based index number of the subtitle entry.
        start_time: Start timestamp string (e.g., '00:01:23,456').
        end_time: End timestamp string (e.g., '00:01:25,789').
        text: The dialogue or caption text (may span multiple lines).
    """

    index: int
    start_time: str
    end_time: str
    text: str

    def to_srt_block(self) -> str:
        """Serialize this entry to standard SRT block format."""
        return f"{self.index}\n{self.start_time} --> {self.end_time}\n{self.text.strip()}\n"


# Regex to match the SRT timestamp line: 00:00:00,000 --> 00:00:00,000
_TIMESTAMP_REGEX = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})"
)


def parse_srt_content(content: str) -> List[SubtitleEntry]:
    """Parse raw SRT content into a list of SubtitleEntry objects.

    Handles different line ending formats (\r\n, \n), extra blank lines,
    and missing/out-of-order sequence numbers.

    Args:
        content: The raw text string of the SRT file.

    Returns:
        A list of parsed SubtitleEntry objects.
    """
    # Normalize line endings and strip BOM if present
    content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", content.strip())

    entries: List[SubtitleEntry] = []
    current_index = 1

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        timestamp_line_idx = -1
        start_time = ""
        end_time = ""

        # Find the line containing the timestamp arrow -->
        for i, line in enumerate(lines):
            match = _TIMESTAMP_REGEX.search(line)
            if match:
                timestamp_line_idx = i
                # Normalize comma separator in timestamps (00:00:00,000)
                start_time = match.group(1).replace(".", ",")
                end_time = match.group(2).replace(".", ",")
                break

        if timestamp_line_idx == -1:
            # Skip invalid blocks without timestamps
            continue

        # Subtitle index: line before timestamp if exists and is numeric, else fallback
        idx = current_index
        if timestamp_line_idx > 0:
            potential_idx = lines[0]
            if potential_idx.isdigit():
                idx = int(potential_idx)

        # Dialogue text is everything after the timestamp line
        text_lines = lines[timestamp_line_idx + 1 :]
        text = "\n".join(text_lines).strip()

        if text:  # Only keep blocks that have actual dialogue
            entries.append(
                SubtitleEntry(
                    index=idx,
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                )
            )
            current_index = idx + 1

    return entries


def read_srt_file(file_path: str | Path) -> List[SubtitleEntry]:
    """Read and parse an SRT file from disk with automatic encoding detection.

    Args:
        file_path: Path to the SRT file.

    Returns:
        List of SubtitleEntry objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file cannot be decoded.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"SRT file not found: {path}")

    # Try common subtitle encodings (UTF-8, UTF-8-sig, Latin-1, cp1252)
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    content = None

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise UnicodeDecodeError(
            "utf-8",
            b"",
            0,
            1,
            f"Failed to decode {path} using encodings: {encodings}",
        )

    return parse_srt_content(content)


def write_srt_file(entries: Sequence[SubtitleEntry], output_path: str | Path) -> Path:
    """Serialize subtitle entries and write them to an SRT file on disk.

    Args:
        entries: Sequence of SubtitleEntry objects.
        output_path: Destination path for the .srt file.

    Returns:
        Path object to the written file.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    formatted_blocks = []
    for i, entry in enumerate(entries, start=1):
        # Renumber indices sequentially to guarantee a clean SRT output
        block = f"{i}\n{entry.start_time} --> {entry.end_time}\n{entry.text.strip()}\n"
        formatted_blocks.append(block)

    full_text = "\n".join(formatted_blocks) + "\n"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    return out_file


def chunk_entries(
    entries: Sequence[SubtitleEntry], chunk_size: int = 40
) -> List[List[SubtitleEntry]]:
    """Split a list of subtitle entries into smaller batches for API processing.

    Args:
        entries: List of SubtitleEntry items.
        chunk_size: Maximum number of entries per batch (default 40).

    Returns:
        A list of entry batches.
    """
    if chunk_size <= 0:
        chunk_size = 40
    return [
        list(entries[i : i + chunk_size])
        for i in range(0, len(entries), chunk_size)
    ]
