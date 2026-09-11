# SPDX-FileCopyrightText: 2026 Oldemar Jesus Gonçalves <oldemar@techboystore.uk>
# SPDX-License-Identifier: MIT

"""Automated unit tests for SRT utilities and extraction logic."""

from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from extractor import SubtitleTrack, find_target_subtitle_track, normalize_language_code
from srt_utils import (
    SubtitleEntry,
    chunk_entries,
    parse_srt_content,
    read_srt_file,
    write_srt_file,
)


class TestSrtUtils(unittest.TestCase):
    """Test SRT parsing, chunking, and serialization."""

    def test_parse_and_write_srt(self) -> None:
        sample_srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,500\n"
            "Hello, world!\n"
            "This is a second line.\n\n"
            "2\n"
            "00:00:05,200 --> 00:00:08,000\n"
            "<i>Goodbye for now.</i>\n"
        )
        entries = parse_srt_content(sample_srt)
        self.assertEqual(len(entries), 2)

        self.assertEqual(entries[0].index, 1)
        self.assertEqual(entries[0].start_time, "00:00:01,000")
        self.assertEqual(entries[0].end_time, "00:00:04,500")
        self.assertEqual(entries[0].text, "Hello, world!\nThis is a second line.")

        self.assertEqual(entries[1].index, 2)
        self.assertEqual(entries[1].text, "<i>Goodbye for now.</i>")

        # Test writing and reading back
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "test.srt"
            write_srt_file(entries, temp_path)
            read_back = read_srt_file(temp_path)
            self.assertEqual(len(read_back), 2)
            self.assertEqual(read_back[0].text, entries[0].text)
            self.assertEqual(read_back[1].text, entries[1].text)

    def test_chunk_entries(self) -> None:
        entries = [
            SubtitleEntry(i, "00:00:00,000", "00:00:01,000", f"Line {i}")
            for i in range(1, 10)
        ]
        chunks = chunk_entries(entries, chunk_size=4)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 4)
        self.assertEqual(len(chunks[1]), 4)
        self.assertEqual(len(chunks[2]), 1)


class TestExtractorLogic(unittest.TestCase):
    """Test subtitle track selection and language matching."""

    def setUp(self) -> None:
        self.tracks = [
            SubtitleTrack(
                stream_index=2,
                subtitle_index=0,
                codec_name="subrip",
                language="spa",
                title="Spanish Latin",
                is_default=False,
                is_forced=False,
            ),
            SubtitleTrack(
                stream_index=3,
                subtitle_index=1,
                codec_name="ass",
                language="eng",
                title="English Signs & Songs",
                is_default=False,
                is_forced=True,
            ),
            SubtitleTrack(
                stream_index=4,
                subtitle_index=2,
                codec_name="ass",
                language="eng",
                title="English Dialogue",
                is_default=True,
                is_forced=False,
            ),
        ]

    def test_default_assumes_english_full_track(self) -> None:
        # Should pick English and prefer non-forced / default
        selected = find_target_subtitle_track(self.tracks, language="eng")
        self.assertIsNotNone(selected)
        self.assertEqual(selected.subtitle_index, 2)
        self.assertEqual(selected.language, "eng")
        self.assertFalse(selected.is_forced)

    def test_select_custom_language(self) -> None:
        selected = find_target_subtitle_track(self.tracks, language="spanish")
        self.assertIsNotNone(selected)
        self.assertEqual(selected.subtitle_index, 0)
        self.assertEqual(selected.language, "spa")

    def test_select_explicit_track_index(self) -> None:
        selected = find_target_subtitle_track(self.tracks, track_index=1)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.subtitle_index, 1)


if __name__ == "__main__":
    unittest.main()
