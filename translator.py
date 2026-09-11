"""Gemini Subtitle Translator.

This module provides translation capabilities for SRT subtitle files using either:
1. The active Google Antigravity session (via `agy` CLI with your existing subscription), or
2. Direct Google GenAI API key (when an API key is specified).

It ensures exact timestamp preservation, subtitle batching, and high-fidelity dialogue translation.
"""

from __future__ import annotations
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tqdm import tqdm

from srt_utils import SubtitleEntry, chunk_entries, read_srt_file, write_srt_file

# Load environment variables from .env if present
load_dotenv()

# JSON Schema definition for structured translation outputs
TRANSLATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["id", "text"],
            },
        }
    },
    "required": ["translations"],
}


LANGUAGE_NAME_MAP: Dict[str, str] = {
    "pt-br": "Brazilian Portuguese (Português do Brasil)",
    "pt-pt": "European Portuguese (Português de Portugal)",
    "pt": "Portuguese (Português)",
    "portuguese": "Portuguese",
    "en": "English",
    "eng": "English",
    "english": "English",
    "es": "Spanish (Español)",
    "spa": "Spanish",
    "es-419": "Latin American Spanish (Español Latinoamericano)",
    "spanish": "Spanish",
    "ja": "Japanese",
    "jpn": "Japanese",
    "japanese": "Japanese",
    "fr": "French",
    "fra": "French",
    "french": "French",
    "de": "German",
    "deu": "German",
    "german": "German",
    "it": "Italian",
    "ita": "Italian",
    "italian": "Italian",
    "zh": "Chinese (Simplified)",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ko": "Korean",
    "kor": "Korean",
    "korean": "Korean",
    "ru": "Russian",
    "rus": "Russian",
    "russian": "Russian",
}


def resolve_language_name(lang: str) -> str:
    """Return descriptive language name for LLM prompting."""
    clean = lang.strip()
    return LANGUAGE_NAME_MAP.get(clean.lower(), clean)


class SubtitleItemTranslation(BaseModel):
    """Schema for an individual translated subtitle entry."""

    id: int = Field(description="The unique subtitle block index number.")
    text: str = Field(description="The natural, contextual translation of the subtitle dialogue.")


class SubtitleBatchResponse(BaseModel):
    """Schema for batch subtitle translation output."""

    translations: List[SubtitleItemTranslation] = Field(
        description="List of translated subtitles in identical order."
    )


def find_agy_binary() -> Optional[str]:
    """Find the Antigravity CLI (`agy`) binary on the system."""
    which_path = shutil.which("agy")
    if which_path:
        return which_path

    known_paths = [
        Path.home() / ".local/share/mise/shims/agy",
        Path.home() / ".gemini/antigravity-ide/bin/agy",
        Path.home() / ".local/bin/agy",
        Path("/usr/local/bin/agy"),
    ]
    for p in known_paths:
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


class GeminiSubtitleTranslator:
    """Translates subtitle entries using Antigravity active session or Gemini API Key."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: int = 40,
        prefer_session: bool = True,
    ) -> None:
        """Initialize the Gemini Subtitle Translator.

        Args:
            api_key: Optional Google Gemini API key. If not provided, will check
                     environment or default to the active Antigravity session.
            model: Optional model name (e.g., 'gemini-3.7-flash-medium', 'gemini-2.5-flash').
            batch_size: Number of subtitle blocks sent per translation batch.
            prefer_session: Whether to prefer the active Antigravity session if no explicit
                            api_key argument is passed.
        """
        self.batch_size = int(
            os.getenv("GEMINI_BATCH_SIZE", str(batch_size))
        )
        self.model = model or os.getenv("GEMINI_MODEL")

        # Determine mode: API key vs Active Antigravity session
        self.api_key = api_key
        self.agy_path = find_agy_binary()

        # If no explicit api_key was passed in constructor, check if session is preferred
        if not self.api_key and prefer_session and self.agy_path:
            self.mode = "session"
            self.genai_client = None
        else:
            # Fall back to env API key or check if available
            env_key = os.getenv("GEMINI_API_KEY")
            if self.api_key or env_key:
                self.api_key = self.api_key or env_key
                self.mode = "api_key"
                from google import genai

                self.genai_client = genai.Client(api_key=self.api_key)
            elif self.agy_path:
                self.mode = "session"
                self.genai_client = None
            else:
                raise ValueError(
                    "No active Antigravity session (`agy`) found and no GEMINI_API_KEY provided.\n"
                    "Please log into Antigravity or provide an API key in .env or via --api-key."
                )

    def _translate_batch_via_session(
        self,
        batch: Sequence[SubtitleEntry],
        target_language: str = "English",
        source_language: Optional[str] = None,
        max_retries: int = 3,
    ) -> List[SubtitleEntry]:
        """Translate a batch using the active Antigravity CLI session (`agy`)."""
        input_data = [{"id": e.index, "text": e.text} for e in batch]
        target_desc = resolve_language_name(target_language)
        source_desc = (
            f"from {resolve_language_name(source_language)} "
            if source_language and source_language.lower() != "auto"
            else ""
        )

        prompt = (
            f"You are a professional subtitle translator. "
            f"Translate the following movie/show subtitle dialogue {source_desc}into natural, fluent {target_desc}.\n"
            f"Preserve formatting tags (e.g. <i>, </i>) if present. "
            f"Translate each item maintaining the exact matching 'id'.\n\n"
            f"Input JSON:\n{json.dumps(input_data, ensure_ascii=False)}"
        )

        cmd = [
            self.agy_path or "agy",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(TRANSLATION_JSON_SCHEMA),
            "--disable-slash-commands",
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )

                output_json: Dict[str, Any] = json.loads(result.stdout)
                structured = output_json.get("structured_output") or {}
                translations_list = structured.get("translations", [])

                if not translations_list:
                    resp_str = output_json.get("response", "")
                    if resp_str:
                        resp_obj = json.loads(resp_str)
                        translations_list = resp_obj.get("translations", [])

                trans_map = {
                    item["id"]: item["text"]
                    for item in translations_list
                    if "id" in item and "text" in item
                }

                translated_entries: List[SubtitleEntry] = []
                for entry in batch:
                    new_text = trans_map.get(entry.index, entry.text)
                    translated_entries.append(
                        SubtitleEntry(
                            index=entry.index,
                            start_time=entry.start_time,
                            end_time=entry.end_time,
                            text=new_text,
                        )
                    )

                return translated_entries

            except Exception as exc:
                if attempt == max_retries:
                    print(
                        f"\n[Warning] Antigravity session translation failed for batch: {exc}. "
                        "Preserving original subtitle lines for this batch."
                    )
                    return list(batch)
                time.sleep(2**attempt)

        return list(batch)

    def _translate_batch_via_api_key(
        self,
        batch: Sequence[SubtitleEntry],
        target_language: str = "English",
        source_language: Optional[str] = None,
        max_retries: int = 3,
    ) -> List[SubtitleEntry]:
        """Translate a batch using direct Google GenAI SDK with API key."""
        from google.genai import types

        input_data = [{"id": e.index, "text": e.text} for e in batch]
        target_desc = resolve_language_name(target_language)
        source_desc = (
            f"from {resolve_language_name(source_language)} "
            if source_language and source_language.lower() != "auto"
            else ""
        )

        system_instruction = (
            f"You are an expert film and TV subtitle localization translator. "
            f"Translate the following movie/show subtitle dialogue {source_desc}into natural, fluent {target_desc}.\n\n"
            f"Guidelines:\n"
            f"1. Preserve subtitle styling tags like <i>, </i>, <b>, </b>, or font tags if present.\n"
            f"2. Maintain conversational nuance, slang, and emotional tone fitting audio pacing.\n"
            f"3. Return the exact same number of items with their matching 'id' values.\n"
            f"4. Do NOT combine or omit any subtitle entries."
        )

        prompt = (
            f"Translate the following subtitle entries into {target_desc}:\n"
            f"```json\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n```"
        )

        model_name = self.model or "gemini-2.5-flash"

        for attempt in range(1, max_retries + 1):
            try:
                assert self.genai_client is not None
                response = self.genai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=SubtitleBatchResponse,
                        temperature=0.3,
                    ),
                )

                if not response.text:
                    raise RuntimeError("Empty response received from Gemini API.")

                parsed_data = json.loads(response.text)
                translations_list = parsed_data.get("translations", [])

                trans_map = {
                    item["id"]: item["text"]
                    for item in translations_list
                    if "id" in item and "text" in item
                }

                translated_entries: List[SubtitleEntry] = []
                for entry in batch:
                    new_text = trans_map.get(entry.index, entry.text)
                    translated_entries.append(
                        SubtitleEntry(
                            index=entry.index,
                            start_time=entry.start_time,
                            end_time=entry.end_time,
                            text=new_text,
                        )
                    )

                return translated_entries

            except Exception as exc:
                if attempt == max_retries:
                    print(
                        f"\n[Warning] API key translation failed for batch: {exc}. "
                        "Preserving original subtitle lines for this batch."
                    )
                    return list(batch)
                time.sleep(2**attempt)

        return list(batch)

    def translate_srt(
        self,
        input_srt_path: str | Path,
        output_srt_path: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
        target_language: str = "English",
        source_language: Optional[str] = None,
        overwrite: bool = True,
    ) -> Path:
        """Read, batch, translate, and write an SRT file.

        Args:
            input_srt_path: Path to the input SRT file.
            output_srt_path: Optional exact output translated SRT file path.
            output_dir: Optional output directory (defaults to 'data/final/').
            target_language: Target translation language (e.g. 'pt-BR', 'English', 'es').
            source_language: Source language name or code (default: auto).
            overwrite: Whether to overwrite if destination file already exists.

        Returns:
            Path to the saved translated SRT file.
        """
        in_path = Path(input_srt_path)
        if not in_path.is_file():
            raise FileNotFoundError(f"Source SRT file not found: {in_path}")

        lang_tag = target_language.strip()
        filename = f"{in_path.stem}.{lang_tag}.srt"

        if output_srt_path is not None:
            final_output_path = Path(output_srt_path)
        elif output_dir is not None:
            final_output_path = Path(output_dir) / filename
        else:
            final_output_path = Path("data") / "final" / filename

        if final_output_path.is_file() and not overwrite:
            print(f"[Info] Final translated file already exists, skipping: {final_output_path}")
            return final_output_path

        entries = read_srt_file(in_path)
        if not entries:
            print(f"[Warning] No subtitle entries found in {in_path}")
            return write_srt_file([], final_output_path)

        batches = chunk_entries(entries, chunk_size=self.batch_size)
        translated_entries: List[SubtitleEntry] = []

        mode_desc = (
            "Active Antigravity Session"
            if self.mode == "session"
            else "Gemini API Key"
        )
        model_desc = f" (Model: {self.model})" if self.model else ""
        resolved_name = resolve_language_name(target_language)

        print(
            f"Translating {len(entries)} subtitles ({len(batches)} batches) "
            f"to {resolved_name} [{lang_tag}] via [{mode_desc}]{model_desc}..."
        )

        with tqdm(total=len(entries), desc="Translating", unit="sub") as pbar:
            for batch in batches:
                if self.mode == "session":
                    translated_batch = self._translate_batch_via_session(
                        batch=batch,
                        target_language=target_language,
                        source_language=source_language,
                    )
                else:
                    translated_batch = self._translate_batch_via_api_key(
                        batch=batch,
                        target_language=target_language,
                        source_language=source_language,
                    )
                translated_entries.extend(translated_batch)
                pbar.update(len(batch))

        saved_path = write_srt_file(translated_entries, final_output_path)
        return saved_path
