<!--
SPDX-FileCopyrightText: 2026 Oldemar Jesus Gonçalves <oldemar@techboystore.uk>

SPDX-License-Identifier: MIT
-->

# AGENT.md - Developer & Agent Guide for `extract-and-translate-srt`

This document provides a concise architectural overview, guidelines, and commands for AI agents and developers working with or extending this codebase.

---

## 1. Project Overview & Goal

`extract-and-translate-srt` is a Python CLI tool and modular library designed to:
1. **Extract subtitle tracks from MKV video containers** into clean `.srt` files using `ffmpeg` and `ffprobe`.
2. **Default Language Assumption**: By default, track extraction assumes English (`eng`), automatically searching for English tracks unless a specific language tag (`-l`) or stream index (`-t`) is provided.
3. **Subtitle Translation via Gemini**:
   - **Default Auth Mode**: Uses the active Google Antigravity session (`agy -p` with JSON schema) without requiring API keys.
   - **Explicit Key Mode**: Supports direct `google-genai` API key usage if `GEMINI_API_KEY` or `--api-key` is supplied.
4. **Full Pipeline**: Extracts subtitles and translates them into natural, fluent target language (default: English) in a single command.

---

## 2. Directory & Module Structure

```
extract-and-translate-srt/
├── .venv/                      # Python virtual environment (Python 3.10+)
├── .env.example                # Template for environment variables (GEMINI_API_KEY, GEMINI_MODEL)
├── .gitignore                  # Git exclusions (.venv, .env, data/, __pycache__, etc.)
├── data/                       # Main output folder (git-ignored)
│   ├── intermediate/           # Extracted subtitles: <original-mkv-filename>.srt
│   └── final/                  # Translated subtitles: <original-mkv-filename>-<lang>.srt
├── requirements.txt            # Python dependencies (google-genai, python-dotenv, rich, tqdm)
├── srt_utils.py                # Pure-Python SRT parser, validator, chunker, serializer
├── extractor.py                # ffprobe stream inspection & ffmpeg SRT extraction logic
├── translator.py               # Dual-mode Gemini translator (Antigravity session vs API key)
├── main.py                     # Rich CLI entrypoint (info, extract, translate, process)
├── test_srt_and_extractor.py   # Unit test suite
├── README.md                   # User-facing documentation
└── AGENT.md                    # Agent architecture and reference guide
```

---

## 3. Core Modules & Responsibilities

### `srt_utils.py`
- **`SubtitleEntry`**: Data class with `index`, `start_time`, `end_time`, `text`.
- **`parse_srt_content(content)` / `read_srt_file(path)`**: Handles mixed line endings (`\r\n`, `\n`), BOM marks (`\ufeff`), encodings (UTF-8, Latin-1, cp1252), and non-standard spacing.
- **`chunk_entries(entries, chunk_size=40)`**: Batches subtitles for LLM processing.
- **`write_srt_file(entries, path)`**: Reconstructs valid `.srt` files with sequential indexing.

### `extractor.py`
- **`list_subtitle_tracks(mkv_path)`**: Runs `ffprobe` (JSON output) to inspect streams where `codec_type == 'subtitle'`. Extracts language tags, stream indices, codecs, and default/forced flags.
- **`find_target_subtitle_track(tracks, language="eng", track_index=None)`**:
  - Matches language codes (`eng`, `en`, `spa`, `jpn`, etc.).
  - Filters out forced/SDH tracks in favor of full dialogue tracks when multiple exist.
  - Falls back to `und` (undetermined) or track 0 if no explicit language match is found.
- **`extract_subtitle_from_mkv(mkv_path, output_srt_path, language, track_index)`**:
  - Executes `ffmpeg -i <mkv> -map 0:s:<idx> -c:s srt <out.srt>`.
  - Rejects image/bitmap subtitle streams (e.g. PGS/VobSub) with helpful guidance.

### `translator.py`
- **`GeminiSubtitleTranslator`**:
  - **Session Mode (`agy`)**: When no API key is specified, invokes the local `agy` CLI with `--output-format json --json-schema ... --disable-slash-commands` to use the user's active Gemini subscription.
  - **API Key Mode (`google-genai`)**: When `GEMINI_API_KEY` is present, uses `genai.Client(api_key=...)` with Pydantic structured output (`SubtitleBatchResponse`).
  - **Preservation Rules**: Subtitle block IDs and exact timestamps are maintained. HTML tags like `<i>...</i>` or `<b>...</b>` are preserved.

### `main.py`
- Exposes CLI commands:
  - `info <input>`: Displays a rich table of all subtitle streams in an MKV.
  - `extract <input>`: Extracts subtitle stream to SRT.
  - `translate <input>`: Translates SRT file(s).
  - `process <input>`: Runs extraction and translation pipeline.
- Supports single file paths and batch processing for directories.

---

## 4. Key Invariants & Behavioral Rules

1. **Always Use `.venv`**: All Python commands must run inside the virtual environment (`.venv/bin/python3`).
2. **Never Break Subtitle Timestamps**: When translating, `start_time` and `end_time` must never be modified by the LLM. Only `text` is translated, mapped 1-to-1 via `index`/`id`.
3. **Active Session Priority**: If no explicit key is provided, prefer the active Antigravity session (`agy`) rather than failing or demanding an API key.
4. **Fallback Handling**: If an LLM translation batch fails after retries, the translator falls back to preserving the original text for that batch without crashing the entire pipeline.

---

## 5. Development & Testing Commands

### Running Unit Tests
```bash
.venv/bin/python3 -m unittest test_srt_and_extractor.py
```

### CLI Verification Commands
```bash
# Check help menus
.venv/bin/python3 main.py --help
.venv/bin/python3 main.py extract --help
.venv/bin/python3 main.py translate --help
.venv/bin/python3 main.py process --help

# Test stream inspection
.venv/bin/python3 main.py info "/path/to/video.mkv"

# Test extraction (assumes English track by default)
.venv/bin/python3 main.py extract "/path/to/video.mkv"

# Test translation via active Antigravity session
.venv/bin/python3 main.py translate "/path/to/subtitle.srt" --target-lang "English"

# Test full pipeline
.venv/bin/python3 main.py process "/path/to/video.mkv" -l jpn --target-lang "English"
```
