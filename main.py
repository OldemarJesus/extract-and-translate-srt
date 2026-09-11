#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Oldemar Jesus Gonçalves <oldemar@techboystore.uk>
# SPDX-License-Identifier: MIT
"""MKV Subtitle Extractor & Gemini Subtitle Translator CLI.

This command-line tool allows you to:
1. Extract subtitle tracks from MKV video files to SRT format (defaulting to English if unspecified).
2. Translate SRT subtitle files using Google Gemini API.
3. Run an end-to-end extraction and translation pipeline on single files or entire directories.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from extractor import extract_subtitle_from_mkv, list_subtitle_tracks
from translator import GeminiSubtitleTranslator

# Load environment configuration (.env)
load_dotenv()
console = Console()


def cmd_info(args: argparse.Namespace) -> None:
    """List subtitle streams in an MKV file."""
    input_path = Path(args.input)
    if not input_path.is_file():
        console.print(f"[red]Error:[/red] File not found: {input_path}")
        sys.exit(1)

    try:
        tracks = list_subtitle_tracks(input_path)
    except Exception as e:
        console.print(f"[red]Error inspecting file:[/red] {e}")
        sys.exit(1)

    if not tracks:
        console.print(f"[yellow]No subtitle tracks found in {input_path.name}[/yellow]")
        return

    table = Table(title=f"Subtitle Tracks in {input_path.name}")
    table.add_column("Track #", justify="center", style="cyan")
    table.add_column("Stream #", justify="center", style="magenta")
    table.add_column("Language", style="green")
    table.add_column("Codec", style="blue")
    table.add_column("Title", style="white")
    table.add_column("Flags", style="yellow")

    for t in tracks:
        flags = []
        if t.is_default:
            flags.append("default")
        if t.is_forced:
            flags.append("forced")
        flag_str = ", ".join(flags) if flags else "-"
        table.add_row(
            str(t.subtitle_index),
            str(t.stream_index),
            t.language,
            t.codec_name,
            t.title or "-",
            flag_str,
        )

    console.print(table)


def find_media_files(path: Path, extensions: List[str]) -> List[Path]:
    """Find all files matching given extensions in a path (file or folder)."""
    if path.is_file():
        return [path] if path.suffix.lower() in extensions else []
    if path.is_dir():
        files: List[Path] = []
        for ext in extensions:
            files.extend(path.glob(f"*{ext}"))
            files.extend(path.glob(f"*{ext.upper()}"))
        return sorted(list(set(files)))
    return []


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract subtitle tracks from MKV file(s)."""
    input_path = Path(args.input)
    files = find_media_files(input_path, [".mkv", ".mp4", ".webm", ".avi"])

    if not files:
        console.print(f"[red]Error:[/red] No valid video files found at {input_path}")
        sys.exit(1)

    out_dir = getattr(args, "intermediate_dir", None) or getattr(args, "output_dir", None) or "data/intermediate"
    console.print(f"[bold green]Found {len(files)} video file(s) to process...[/bold green]")
    console.print(f"[dim]Outputs will be saved to: {args.output or out_dir}[/dim]\n")

    success_count = 0
    for video_file in files:
        console.print(f"[cyan]Processing:[/cyan] {video_file.name}")
        try:
            out_file = extract_subtitle_from_mkv(
                mkv_path=video_file,
                output_srt_path=args.output if (len(files) == 1 and args.output) else None,
                output_dir=out_dir,
                language=args.lang,
                track_index=args.track,
                overwrite=args.overwrite,
            )
            console.print(f"[green]✓ Extracted SRT:[/green] {out_file}\n")
            success_count += 1
        except Exception as e:
            console.print(f"[red]✗ Failed to extract {video_file.name}:[/red] {e}\n")

    console.print(f"[bold]Extraction finished:[/bold] {success_count}/{len(files)} succeeded.")


def cmd_translate(args: argparse.Namespace) -> None:
    """Translate SRT file(s) using Gemini."""
    input_path = Path(args.input)
    files = find_media_files(input_path, [".srt"])

    if not files:
        console.print(f"[red]Error:[/red] No .srt files found at {input_path}")
        sys.exit(1)

    try:
        translator = GeminiSubtitleTranslator(
            api_key=args.api_key,
            model=args.model,
            batch_size=args.batch_size,
        )
    except Exception as e:
        console.print(f"[red]Error initializing translator:[/red] {e}")
        sys.exit(1)

    out_dir = getattr(args, "final_dir", None) or getattr(args, "output_dir", None) or "data/final"
    console.print(f"[bold green]Found {len(files)} SRT file(s) to translate...[/bold green]")
    console.print(f"[dim]Outputs will be saved to: {args.output or out_dir}[/dim]\n")

    for srt_file in files:
        console.print(f"[cyan]Translating:[/cyan] {srt_file.name}")
        try:
            out_file = translator.translate_srt(
                input_srt_path=srt_file,
                output_srt_path=args.output if (len(files) == 1 and args.output) else None,
                output_dir=out_dir,
                target_language=args.target_lang,
                source_language=args.source_lang,
                overwrite=args.overwrite,
            )
            console.print(f"[green]✓ Translated SRT saved to:[/green] {out_file}\n")
        except Exception as e:
            console.print(f"[red]✗ Translation failed for {srt_file.name}:[/red] {e}\n")


def cmd_pipeline(args: argparse.Namespace) -> None:
    """Full pipeline: Extract subtitle from MKV and translate it with Gemini."""
    input_path = Path(args.input)
    files = find_media_files(input_path, [".mkv", ".mp4", ".webm", ".avi"])

    if not files:
        console.print(f"[red]Error:[/red] No valid video files found at {input_path}")
        sys.exit(1)

    try:
        translator = GeminiSubtitleTranslator(
            api_key=args.api_key,
            model=args.model,
            batch_size=args.batch_size,
        )
    except Exception as e:
        console.print(f"[red]Error initializing translator:[/red] {e}")
        sys.exit(1)

    intermediate_dir = Path(args.intermediate_dir or "data/intermediate")
    final_dir = Path(args.final_dir or "data/final")

    console.print(
        f"[bold green]Running Pipeline on {len(files)} video file(s)...[/bold green]"
    )
    console.print(f"[dim]Intermediate folder: {intermediate_dir}[/dim]")
    console.print(f"[dim]Final folder:        {final_dir}[/dim]\n")

    for video_file in files:
        console.print(f"[bold blue]=== Processing {video_file.name} ===[/bold blue]")
        try:
            # Step 1: Extract SRT to intermediate folder (data/intermediate/<name>.srt)
            console.print(
                f"[cyan]Step 1: Extracting subtitle to '{intermediate_dir}' (lang filter: '{args.lang}')[/cyan]"
            )
            extracted_srt = extract_subtitle_from_mkv(
                mkv_path=video_file,
                output_dir=intermediate_dir,
                language=args.lang,
                track_index=args.track,
                overwrite=args.overwrite,
            )
            console.print(f"[green]✓ Intermediate SRT:[/green] {extracted_srt}")

            # Step 2: Translate SRT to final folder (data/final/<name>.<lang>.srt)
            target_slug = args.target_lang.strip()
            final_srt_path = final_dir / f"{video_file.stem}.{target_slug}.srt"

            console.print(
                f"[cyan]Step 2: Translating to '{args.target_lang}' -> '{final_srt_path}'[/cyan]"
            )

            out_file = translator.translate_srt(
                input_srt_path=extracted_srt,
                output_srt_path=final_srt_path,
                target_language=args.target_lang,
                source_language=args.source_lang,
                overwrite=args.overwrite,
            )
            console.print(f"[green]✓ Final translated SRT:[/green] {out_file}\n")

        except Exception as e:
            console.print(f"[red]✗ Pipeline failed for {video_file.name}:[/red] {e}\n")


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Extract SRT from MKV and Translate Subtitles using Google Gemini.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: info
    info_parser = subparsers.add_parser(
        "info", help="List all subtitle tracks inside an MKV file"
    )
    info_parser.add_argument("input", help="Path to the MKV file")

    # Command: extract
    extract_parser = subparsers.add_parser(
        "extract", help="Extract subtitles from MKV file(s) into SRT"
    )
    extract_parser.add_argument("input", help="Path to MKV file or directory")
    extract_parser.add_argument(
        "-o", "--output", help="Optional exact output SRT file path (for single file)"
    )
    extract_parser.add_argument(
        "-d", "--output-dir", "--intermediate-dir",
        dest="intermediate_dir",
        default="data/intermediate",
        help="Destination folder for extracted intermediate SRT files (default: data/intermediate)",
    )
    extract_parser.add_argument(
        "-l",
        "--lang",
        default="eng",
        help="Target language code to extract (assumes 'eng' by default)",
    )
    extract_parser.add_argument(
        "-t",
        "--track",
        type=int,
        default=None,
        help="Explicit subtitle track index (0-based)",
    )
    extract_parser.add_argument(
        "--no-overwrite",
        action="store_false",
        dest="overwrite",
        help="Do not overwrite existing SRT files",
    )

    # Command: translate
    translate_parser = subparsers.add_parser(
        "translate", help="Translate SRT file(s) using Gemini (active Antigravity session by default)"
    )
    translate_parser.add_argument("input", help="Path to .srt file or directory")
    translate_parser.add_argument(
        "-o", "--output", help="Optional exact output translated SRT file path"
    )
    translate_parser.add_argument(
        "-d", "--output-dir", "--final-dir",
        dest="final_dir",
        default="data/final",
        help="Destination folder for translated final SRT files (default: data/final)",
    )
    translate_parser.add_argument(
        "--target-lang",
        default="English",
        help="Destination language for translation",
    )
    translate_parser.add_argument(
        "--source-lang",
        default="auto",
        help="Source language of the subtitles (e.g. 'Japanese', 'Spanish', 'auto')",
    )
    translate_parser.add_argument(
        "--model",
        default=None,
        help="Gemini model name (e.g. gemini-3.7-flash-medium, gemini-3.8-flash-low)",
    )
    translate_parser.add_argument(
        "--batch-size",
        type=int,
        default=40,
        help="Number of subtitle entries per translation request",
    )
    translate_parser.add_argument(
        "--api-key",
        default=None,
        help="Explicit Google Gemini API key (optional; defaults to active Antigravity session)",
    )
    translate_parser.add_argument(
        "--no-overwrite",
        action="store_false",
        dest="overwrite",
        help="Do not overwrite existing SRT files",
    )

    # Command: process (full pipeline)
    pipeline_parser = subparsers.add_parser(
        "process",
        help="Full Pipeline: Extract subtitle to data/intermediate/ and translate to data/final/",
    )
    pipeline_parser.add_argument("input", help="Path to MKV file or directory")
    pipeline_parser.add_argument(
        "--intermediate-dir",
        default="data/intermediate",
        help="Folder for extracted intermediate SRT files (default: data/intermediate)",
    )
    pipeline_parser.add_argument(
        "--final-dir",
        default="data/final",
        help="Folder for translated final SRT files (default: data/final)",
    )
    pipeline_parser.add_argument(
        "-l",
        "--lang",
        default="eng",
        help="Subtitle track language code to extract (assumes 'eng' by default)",
    )
    pipeline_parser.add_argument(
        "-t",
        "--track",
        type=int,
        default=None,
        help="Explicit subtitle track index (0-based)",
    )
    pipeline_parser.add_argument(
        "--target-lang",
        default="English",
        help="Target language for translation",
    )
    pipeline_parser.add_argument(
        "--source-lang",
        default="auto",
        help="Source language of the subtitles (e.g. 'Japanese', 'Spanish', 'auto')",
    )
    pipeline_parser.add_argument(
        "--model",
        default=None,
        help="Gemini model name (e.g. gemini-3.7-flash-medium, gemini-3.8-flash-low)",
    )
    pipeline_parser.add_argument(
        "--batch-size",
        type=int,
        default=40,
        help="Number of subtitle entries per translation request",
    )
    pipeline_parser.add_argument(
        "--api-key",
        default=None,
        help="Explicit Google Gemini API key (optional; defaults to active Antigravity session)",
    )
    pipeline_parser.add_argument(
        "--no-overwrite",
        action="store_false",
        dest="overwrite",
        help="Do not overwrite existing SRT files",
    )

    # Default to showing help if no subcommand is provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.command == "info":
        cmd_info(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command == "translate":
        cmd_translate(args)
    elif args.command == "process":
        cmd_pipeline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
