#!/usr/bin/env python3
"""
Meeting Transcriber CLI

Usage:
    python cli.py video.mp4
    python cli.py audio.wav -m small -l en -f srt
    python cli.py meeting.mp4 --diarize --min-speakers 2 --max-speakers 4
"""
import argparse
import asyncio
import sys
from pathlib import Path

import config
from transcriber import transcribe, format_output, save_result, get_audio_duration


def print_progress(progress: int, message: str):
    """Print progress bar to terminal."""
    bar_width = 40
    filled = int(bar_width * progress / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\r[{bar}] {progress}% - {message}", end="", flush=True)
    if progress >= 100:
        print()  # New line when done


async def progress_callback(data: dict):
    """Async wrapper for progress printing. Accepts dict from transcriber."""
    progress = data.get("progress", 0)
    message = data.get("message", "")
    print_progress(progress, message)


async def run_transcription(args):
    """Run transcription with given arguments."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    if file_path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file type: {file_path.suffix}", file=sys.stderr)
        print(f"Supported: {', '.join(config.SUPPORTED_EXTENSIONS)}", file=sys.stderr)
        return 1

    # Show file info
    duration = get_audio_duration(file_path)
    print(f"File: {file_path.name}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Model: {args.model}")
    print(f"Language: {config.SUPPORTED_LANGUAGES.get(args.language, args.language)}")
    print(f"Format: {args.format}")
    if args.diarize:
        print(f"Diarization: enabled (speakers: {args.min_speakers or '?'}-{args.max_speakers or '?'})")
    print()

    try:
        # Run transcription
        result = await transcribe(
            file_path=file_path,
            model_name=args.model,
            output_format=args.format,
            language=args.language,
            diarize=args.diarize,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            progress_callback=progress_callback,
        )

        print()  # New line after progress

        # Output result
        if args.output:
            output_path = Path(args.output)
            formatted = format_output(result, args.format)
            output_path.write_text(formatted, encoding="utf-8")
            print(f"Saved to: {output_path}")
        else:
            # Save to results directory
            output_path = save_result(result, file_path.name, args.format)
            print(f"Saved to: {output_path}")

        # Show stats
        word_count = len(result.get("text", "").split())
        print(f"\nStats: {word_count} words, language: {result.get('language', 'unknown')}")
        if result.get("speakers", 0) > 0:
            print(f"Speakers detected: {result['speakers']}")

        # Preview if text format
        if args.format == "txt" and not args.quiet:
            preview = result.get("text", "")[:500]
            if len(result.get("text", "")) > 500:
                preview += "..."
            print(f"\nPreview:\n{'-'*40}\n{preview}\n{'-'*40}")

        return 0

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 130
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files using Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                    # Basic transcription
  %(prog)s audio.wav -m small           # Use small model
  %(prog)s meeting.mp4 -l en -f srt     # English, SRT format
  %(prog)s call.mp3 --diarize           # With speaker identification
  %(prog)s video.mp4 -o transcript.txt  # Custom output path
        """
    )

    parser.add_argument("file", nargs="?", help="Audio or video file to transcribe")

    parser.add_argument(
        "-m", "--model",
        choices=list(config.AVAILABLE_MODELS.keys()),
        default=config.DEFAULT_MODEL,
        help=f"Whisper model (default: {config.DEFAULT_MODEL})"
    )

    parser.add_argument(
        "-l", "--language",
        choices=list(config.SUPPORTED_LANGUAGES.keys()),
        default=config.DEFAULT_LANGUAGE,
        help="Language code or 'auto' for detection (default: auto)"
    )

    parser.add_argument(
        "-f", "--format",
        choices=config.OUTPUT_FORMATS,
        default="txt",
        help="Output format (default: txt)"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: results directory)"
    )

    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization (requires HF_TOKEN)"
    )

    parser.add_argument(
        "--min-speakers",
        type=int,
        help="Minimum number of speakers (for diarization)"
    )

    parser.add_argument(
        "--max-speakers",
        type=int,
        help="Maximum number of speakers (for diarization)"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress preview output"
    )

    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List all supported languages and exit"
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available models and exit"
    )

    args = parser.parse_args()

    # Handle list commands
    if args.list_languages:
        print("Supported languages:")
        for code, name in config.SUPPORTED_LANGUAGES.items():
            print(f"  {code:6} - {name}")
        return 0

    if args.list_models:
        print("Available models:")
        for model_id, info in config.AVAILABLE_MODELS.items():
            print(f"  {model_id:10} - {info['name']}: {info['description']}")
        return 0

    # File is required for transcription
    if not args.file:
        parser.error("file is required for transcription")

    # Run transcription
    return asyncio.run(run_transcription(args))


if __name__ == "__main__":
    sys.exit(main())
