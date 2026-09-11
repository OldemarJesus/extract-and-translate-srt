# MKV Subtitle Extractor & Gemini Subtitle Translator

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

1. Navigate to the project directory:
   ```bash
   cd /home/oldemar/Projects/extract-and-translate-srt
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

## 🚀 Usage Guide

You can run the tool via `.venv/bin/python3 main.py` or by activating the virtual environment first (`source .venv/bin/activate`).

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
  python main.py extract "/run/user/1000/gvfs/smb-share:server=nas.techboystore.uk,share=docker/containers/jellyfin/media/tvshows/Show Name/Season 01/"
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
  python main.py translate "data/intermediate/S01E01.srt" --target-lang "English"
  ```
  *Output:* `data/final/S01E01-english.srt`

- **Batch translate all extracted subtitles in `data/intermediate/`:**
  ```bash
  python main.py translate "data/intermediate/" --target-lang "English"
  ```

---

### 4. Full Pipeline: Extract & Translate in One Step (`process`)

Scans all MKV files in a folder, extracts them to `data/intermediate/<name>.srt`, and translates them into `data/final/<name>-<lang>.srt`:

```bash
python main.py process "/run/user/1000/gvfs/smb-share:server=nas.techboystore.uk,share=docker/containers/jellyfin/media/tvshows/The Most Heretical Last Boss Queen - From Villainess to Savior/The Most Heretical Last Boss Queen - From Villainess to Savior - S01E -/" --target-lang "English"
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
    target_language="English"
)
print(f"Translated: {translated_srt}")
```

---

## 📁 Project Structure

```
extract-and-translate-srt/
├── .venv/                      # Python Virtual Environment
├── .env.example                # Configuration template for Gemini API key
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── srt_utils.py                # SRT parsing, timing validation, chunking, serialization
├── extractor.py                # ffprobe stream inspection & ffmpeg SRT extraction
├── translator.py               # Gemini batch translation engine with schema validation
├── main.py                     # Rich CLI interface (info, extract, translate, process)
├── test_srt_and_extractor.py   # Automated unit tests
└── README.md                   # Documentation and usage guide
```

---

## 🧪 Running Tests

To verify that the SRT parser and extractor track logic are working correctly:

```bash
.venv/bin/python3 -m unittest test_srt_and_extractor.py
```
