# MKV Subtitle Extractor & Gemini Subtitle Translator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/oldemego/extract-and-translate-srt/actions/workflows/ci.yml/badge.svg)](https://github.com/oldemego/extract-and-translate-srt/actions)
[![REUSE status](https://api.reuse.software/badge/github.com/oldemego/extract-and-translate-srt)](https://api.reuse.software/info/github.com/oldemego/extract-and-translate-srt)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![Created with](https://img.shields.io/badge/Created%20with-Gemini%203.7%20Flash-4285F4.svg?logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)

A fast, Python-based CLI tool and library to:
1. **Extract subtitle tracks from MKV** video files directly into standard `.srt` format using `ffmpeg`/`ffprobe` (automatically assuming English unless specified).
2. **Translate SRT subtitles using Google Gemini** (`gemini-2.5-flash` or customizable models), preserving exact timestamps, subtitle sequence IDs, and formatting tags (e.g. `<i>...</i>`).
3. **Run end-to-end pipelines** on single videos or entire directories.

---

## 🛠️ Requirements & Authentication

- **Python 3.10+** (managed in `.venv`)
- **FFmpeg & FFprobe** (installed on system)
- **Active Antigravity Session (Default)**: If you are logged into Antigravity (`agy`), the script **automatically** uses your active subscription without needing any API key!
- **Optional API Key**: If you prefer using a standalone Gemini API key, you can provide `GEMINI_API_KEY` in `.env` or pass `--api-key <KEY>`.

---

## 📦 Installation & Setup

1. Clone repository and navigate to the project directory:
   ```bash
   git clone https://github.com/oldemego/extract-and-translate-srt.git
   cd extract-and-translate-srt
   ```

2. Create and activate the Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. *(Optional)* Configure a standalone API key or model preferences:
   ```bash
   cp .env.example .env
   ```
   *(By default, if no API key is specified, it seamlessly uses your active Antigravity session).*

---

## 📁 Data Directory Structure

By default, all generated outputs are organized into structured, git-ignored subdirectories:

```
data/
├── intermediate/       # Raw extracted subtitles: <mkv-name>.srt
└── final/              # Translated subtitles:    <mkv-name>-<lang>.srt
```

---

## 🚀 Usage Guide

You can run the tool via `.venv/bin/python3 main.py` or by activating the virtual environment (`source .venv/bin/activate`).

### 1. Inspect Subtitle Tracks in an MKV File (`info`)

Inspect available subtitle tracks, codecs, language tags, and titles:

```bash
python main.py info "/path/to/show/Episode.mkv"
```

---

### 2. Extract Subtitles (`extract`)

Extracts subtitle tracks from MKV video file(s) into standard `.srt`. **Assumes English (`eng`) by default and saves into `data/intermediate/`**.

- **Single file:**
  ```bash
  python main.py extract "/path/to/show/S01E01.mkv"
  ```
  *Output:* `data/intermediate/S01E01.srt`

- **Batch extract an entire TV show folder (e.g., local or SMB / NAS mount):**
  ```bash
  python main.py extract "/path/to/tvshows/Show Name/Season 01/"
  ```
  *Extracts all MKV episodes into `data/intermediate/<Episode_Name>.srt`.*

- **Extract a different language track (e.g., Japanese `-l jpn`, Spanish `-l spa`):**
  ```bash
  python main.py extract "/path/to/folder/" -l jpn
  ```

- **Specify an exact track index (`-t 0`, `-t 1`):**
  ```bash
  python main.py extract "/path/to/folder/" -t 1
  ```

---

### 3. Translate SRT Files (`translate`)

Translates `.srt` subtitle files using Gemini and saves the result to `data/final/<name>-<lang>.srt`.

- **Translate a single SRT:**
  ```bash
  python main.py translate "data/intermediate/S01E01.srt" --target-lang "Portuguese (Brazil)"
  ```
  *Output:* `data/final/S01E01.pt-BR.srt`

- **Batch translate all extracted subtitles in `data/intermediate/`:**
  ```bash
  python main.py translate "data/intermediate/" --target-lang "Portuguese (Brazil)"
  ```

---

### 4. Full Pipeline: Extract & Translate in One Step (`process`)

Scans all MKV files in a folder, extracts them to `data/intermediate/<name>.srt`, and translates them into `data/final/<name>-<lang>.srt`:

```bash
python main.py process "/path/to/tvshows/Season 01/" --target-lang "Portuguese (Brazil)"
```

**Resume / Skip Existing:**
Add `--no-overwrite` to skip any episode that has already been extracted or translated.

---

## 🐍 Python Library API Usage

You can also import and use the modules directly in your own Python scripts:

```python
from extractor import extract_subtitle_from_mkv, list_subtitle_tracks
from translator import GeminiSubtitleTranslator

# 1. Inspect subtitle streams
tracks = list_subtitle_tracks("video.mkv")
for track in tracks:
    print(track)

# 2. Extract English (default) or specified track to SRT
srt_path = extract_subtitle_from_mkv("video.mkv", language="eng")
print(f"Extracted: {srt_path}")

# 3. Translate SRT using Gemini
translator = GeminiSubtitleTranslator()
translated_srt = translator.translate_srt(
    input_srt_path=srt_path,
    target_language="Portuguese (Brazil)"
)
print(f"Translated: {translated_srt}")
```

---

## 📁 Project Structure

```
extract-and-translate-srt/
├── .github/
│   ├── ISSUE_TEMPLATE/         # GitHub issue templates (Bug report, feature request)
│   ├── PULL_REQUEST_TEMPLATE.md# Pull request template with checklist
│   └── workflows/ci.yml        # GitHub Actions CI workflow
├── LICENSES/
│   └── MIT.txt                 # REUSE / SPDX License specification
├── .env.example                # Configuration template for Gemini API key
├── .gitignore                  # Git ignore rules
├── CITATION.cff                # Citation metadata format
├── CODE_OF_CONDUCT.md          # Contributor Covenant v2.1
├── CONTRIBUTING.md             # Contribution guidelines & Developer Certificate of Origin
├── LICENSE                     # MIT License
├── README.md                   # Documentation and usage guide
├── SECURITY.md                 # Vulnerability disclosure and security policy
├── requirements.txt            # Python dependencies
├── srt_utils.py                # SRT parsing, timing validation, chunking, serialization
├── extractor.py                # ffprobe stream inspection & ffmpeg SRT extraction
├── translator.py               # Gemini batch translation engine with schema validation
├── main.py                     # Rich CLI interface (info, extract, translate, process)
└── test_srt_and_extractor.py   # Automated unit tests
```

---

## 🧪 Running Tests

To run the automated unit test suite:

```bash
python3 -m unittest test_srt_and_extractor.py
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Please check our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

---

## 🛡️ Security

If you discover a potential security issue, please consult our [Security Policy](SECURITY.md) for reporting procedures.

---

## 🤖 Acknowledgments & Creation

This project was entirely created with **[Gemini 3.7 Flash](https://deepmind.google/technologies/gemini/)** and carefully reviewed, validated, and tested by **Oldemar Jesus Gonçalves**.

---

## 📄 License & Citation

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) or [`LICENSES/MIT.txt`](LICENSES/MIT.txt) for more information.

If you use this project in research or software, you can cite it using the metadata in [`CITATION.cff`](CITATION.cff).
