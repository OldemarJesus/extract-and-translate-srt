# SPDX-FileCopyrightText: 2026 Oldemar Jesus Gonçalves <oldemego@gmail.com>
# SPDX-License-Identifier: MIT

"""MKV Subtitle Extractor using ffprobe and ffmpeg.

This module provides tools to inspect subtitle streams inside MKV files,
select subtitle streams by language code (defaulting to English) or track index,
and extract/convert them into standard .srt subtitle files.
"""

from __future__ import annotations
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SubtitleTrack:
    """Metadata for an individual subtitle stream in a media file."""

    stream_index: int  # Global stream index (e.g., 2)
    subtitle_index: int  # 0-based index among subtitle streams (e.g., 0 for first subtitle stream)
    codec_name: str  # e.g., 'subrip', 'ass', 'ssa', 'hdmv_pgs_subtitle'
    language: str  # ISO 639-2 or ISO 639-1 code (e.g., 'eng', 'en', 'spa', 'und')
    title: str  # Stream title tag (e.g., 'English (SDH)', 'Dialogue')
    is_default: bool
    is_forced: bool

    def __str__(self) -> str:
        flags = []
        if self.is_default:
            flags.append("default")
        if self.is_forced:
            flags.append("forced")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        title_str = f" - '{self.title}'" if self.title else ""
        return (
            f"Track #{self.subtitle_index} (Stream #{self.stream_index}): "
            f"Language='{self.language}', Codec='{self.codec_name}'{title_str}{flag_str}"
        )


def check_ffmpeg_installed() -> None:
    """Ensure ffmpeg and ffprobe are available in the system PATH.

    Raises:
        RuntimeError: If either ffmpeg or ffprobe is missing.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is not installed or not in PATH. Please install ffmpeg."
        )
    if not shutil.which("ffprobe"):
        raise RuntimeError(
            "ffprobe is not installed or not in PATH. Please install ffprobe."
        )


def list_subtitle_tracks(mkv_path: str | Path) -> List[SubtitleTrack]:
    """Inspect an MKV file and return a list of all subtitle tracks.

    Args:
        mkv_path: Path to the MKV media file.

    Returns:
        List of SubtitleTrack metadata objects.

    Raises:
        FileNotFoundError: If the MKV file does not exist.
        RuntimeError: If ffprobe execution fails.
    """
    check_ffmpeg_installed()
    video_path = Path(mkv_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"MKV video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            f"ffprobe failed to read file {video_path}: {err.stderr}"
        ) from err

    probe_data: Dict[str, Any] = json.loads(result.stdout)
    streams = probe_data.get("streams", [])

    subtitle_tracks: List[SubtitleTrack] = []
    sub_idx_counter = 0

    for stream in streams:
        if stream.get("codec_type") == "subtitle":
            tags = stream.get("tags", {})
            disposition = stream.get("disposition", {})

            lang = (
                tags.get("language")
                or tags.get("LANGUAGE")
                or "und"  # 'und' = undetermined
            ).lower()
            title = tags.get("title") or tags.get("TITLE") or ""

            is_default = bool(disposition.get("default", 0))
            is_forced = bool(disposition.get("forced", 0))

            track = SubtitleTrack(
                stream_index=int(stream.get("index", 0)),
                subtitle_index=sub_idx_counter,
                codec_name=str(stream.get("codec_name", "unknown")),
                language=lang,
                title=title,
                is_default=is_default,
                is_forced=is_forced,
            )
            subtitle_tracks.append(track)
            sub_idx_counter += 1

    return subtitle_tracks


def normalize_language_code(lang: str) -> List[str]:
    """Map common language abbreviations to equivalent codes for matching.

    Args:
        lang: Language string or code (e.g. 'en', 'eng', 'english', 'spanish', 'es').

    Returns:
        List of candidate code strings (e.g. ['eng', 'en', 'english']).
    """
    lang_clean = lang.strip().lower()
    mapping: Dict[str, List[str]] = {
        "en": ["en", "eng", "english"],
        "eng": ["en", "eng", "english"],
        "english": ["en", "eng", "english"],
        "es": ["es", "spa", "spanish", "español"],
        "spa": ["es", "spa", "spanish", "español"],
        "spanish": ["es", "spa", "spanish", "español"],
        "ja": ["ja", "jpn", "japanese"],
        "jpn": ["ja", "jpn", "japanese"],
        "japanese": ["ja", "jpn", "japanese"],
        "fr": ["fr", "fra", "fre", "french"],
        "fra": ["fr", "fra", "fre", "french"],
        "de": ["de", "ger", "deu", "german"],
        "it": ["it", "ita", "italian"],
        "pt": ["pt", "por", "portuguese"],
        "zh": ["zh", "chi", "zho", "chinese"],
        "ko": ["ko", "kor", "korean"],
        "ru": ["ru", "rus", "russian"],
    }
    return mapping.get(lang_clean, [lang_clean])


def find_target_subtitle_track(
    tracks: List[SubtitleTrack],
    language: str = "eng",
    track_index: Optional[int] = None,
) -> Optional[SubtitleTrack]:
    """Find the best matching subtitle track based on index or language.

    Args:
        tracks: List of available SubtitleTrack objects.
        language: Language code to match (default 'eng'). Assumes English unless specified.
        track_index: Optional explicit subtitle index (0-based).

    Returns:
        The matched SubtitleTrack, or the first available track as fallback, or None.
    """
    if not tracks:
        return None

    # If track_index is explicitly requested
    if track_index is not None:
        for t in tracks:
            if t.subtitle_index == track_index:
                return t
        raise ValueError(
            f"Requested subtitle track index {track_index} was not found. "
            f"Available indices: {[t.subtitle_index for t in tracks]}"
        )

    # Match by language candidates
    candidates = normalize_language_code(language)
    matched_tracks: List[SubtitleTrack] = []

    for t in tracks:
        # Check language tag or title mentioning the language
        if t.language.lower() in candidates:
            matched_tracks.append(t)
        elif any(c in t.title.lower() for c in candidates):
            matched_tracks.append(t)

    if matched_tracks:
        # Prefer full dialogue over forced subtitles if multiple exist
        non_forced = [t for t in matched_tracks if not t.is_forced]
        if non_forced:
            # Prefer default if set
            defaults = [t for t in non_forced if t.is_default]
            return defaults[0] if defaults else non_forced[0]
        return matched_tracks[0]

    # Fallback: if 'und' (undetermined) exists and language was default 'eng'
    und_tracks = [t for t in tracks if t.language in ("und", "")]
    if und_tracks:
        return und_tracks[0]

    # Final fallback: return the first subtitle track
    return tracks[0]


DEFAULT_INTERMEDIATE_DIR = Path("data") / "intermediate"


def extract_subtitle_from_mkv(
    mkv_path: str | Path,
    output_srt_path: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
    language: str = "eng",
    track_index: Optional[int] = None,
    overwrite: bool = True,
) -> Path:
    """Extract a subtitle track from an MKV file and convert it into an SRT file.

    Args:
        mkv_path: Path to the input MKV file.
        output_srt_path: Optional exact destination file path.
        output_dir: Optional output directory (defaults to 'data/intermediate/').
        language: Subtitle language code to search for (default 'eng').
        track_index: Optional explicit subtitle track index (0-based).
        overwrite: Whether to overwrite existing output files.

    Returns:
        Path to the generated .srt file.

    Raises:
        FileNotFoundError: If the MKV file is not found.
        ValueError: If no subtitle tracks exist or track is bitmap-based (PGS/VobSub).
        RuntimeError: If ffmpeg fails during extraction.
    """
    video_path = Path(mkv_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"MKV video file not found: {video_path}")

    tracks = list_subtitle_tracks(video_path)
    if not tracks:
        raise ValueError(f"No subtitle tracks found in {video_path.name}")

    target_track = find_target_subtitle_track(
        tracks, language=language, track_index=track_index
    )
    if target_track is None:
        raise ValueError(
            f"Could not find a suitable subtitle track in {video_path.name}"
        )

    # Check for unsupported bitmap subtitles (e.g., PGS, VOBSUB)
    bitmap_codecs = {"hdmv_pgs_subtitle", "dvd_subtitle", "pgssub", "vobsub"}
    if target_track.codec_name.lower() in bitmap_codecs:
        raise ValueError(
            f"Track #{target_track.subtitle_index} uses image/bitmap codec '{target_track.codec_name}'. "
            "ffmpeg cannot directly convert image subtitles into text SRT without OCR."
        )

    filename = f"{video_path.stem}.srt"

    if output_srt_path is not None:
        final_output_path = Path(output_srt_path)
    elif output_dir is not None:
        final_output_path = Path(output_dir) / filename
    else:
        final_output_path = DEFAULT_INTERMEDIATE_DIR / filename

    if final_output_path.is_file() and not overwrite:
        return final_output_path

    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-i",
        str(video_path),
        "-map",
        f"0:s:{target_track.subtitle_index}",
        "-c:s",
        "srt",
        str(final_output_path),
    ]

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            f"ffmpeg failed to extract subtitle from {video_path.name}: {err.stderr}"
        ) from err

    return final_output_path
