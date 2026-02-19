#!/usr/bin/env python3
"""
YouTube Sales Transcript Analyzer — Main Entry Point

Pipeline:
  YouTube URL
    → fetch transcript
    → Claude extracts structured sales insights (JSON)
    → Claude generates sales agent system prompt
    → save artifacts to disk
    → (optional) launch interactive sales agent

Usage:
  python main.py <youtube_url> [options]
  python main.py --interactive <saved_prompt_file>
"""

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

import anthropic

from transcript import extract_video_id, fetch_transcript, format_transcript_with_timestamps
from analyzer import analyze_transcript, pretty_print_analysis
from agent import SalesAgent, generate_agent_prompt, run_interactive_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIVIDER = "─" * 65


def print_step(n: int, total: int, message: str):
    print(f"\n[{n}/{total}] {message}")


def save_artifact(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"       Saved → {path}")


def load_env_api_key() -> str | None:
    """Try loading ANTHROPIC_API_KEY from environment or a .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(url: str, api_key: str, output_dir: Path, launch_agent: bool, model: str):
    """Full pipeline: URL → transcript → analysis → agent prompt → (optional agent)."""

    client = anthropic.Anthropic(api_key=api_key)

    # 1. Extract video ID
    print_step(1, 5, "Extracting video ID...")
    video_id = extract_video_id(url)
    if not video_id:
        print("ERROR: Cannot parse a YouTube video ID from the provided URL.")
        sys.exit(1)
    print(f"       Video ID: {video_id}")

    # 2. Fetch transcript
    print_step(2, 5, "Fetching YouTube transcript...")
    result = fetch_transcript(video_id)
    transcript_text = result["text"]
    segments = result["segments"]
    lang = result["language"]
    translated = result["was_translated"]
    char_count = len(transcript_text)
    word_count = len(transcript_text.split())
    print(f"       Language : {lang}{'  (auto-translated to English)' if translated else ''}")
    print(f"       Length   : {word_count:,} words  /  {char_count:,} characters")

    # 3. Analyze transcript with Claude
    print_step(3, 5, "Analyzing sales content with Claude (this may take a moment)...")
    analysis = analyze_transcript(transcript_text, client, model=model)
    if "parse_error" in analysis:
        print("       WARNING: Claude returned non-JSON output — stored as raw text.")
    else:
        print(f"       Extracted {sum(len(v) if isinstance(v, list) else 1 for v in analysis.values())} insight items.")

    # 4. Generate sales agent prompt
    print_step(4, 5, "Generating sales agent system prompt with Claude...")
    agent_prompt = generate_agent_prompt(analysis, client, model=model)
    print(f"       Prompt length: {len(agent_prompt):,} characters")

    # 5. Save all artifacts
    print_step(5, 5, "Saving artifacts...")
    base = output_dir / f"sales_{video_id}"
    save_artifact(base / "transcript.txt", transcript_text)
    save_artifact(base / "transcript_timestamped.txt", format_transcript_with_timestamps(segments))
    save_artifact(base / "analysis.json", json.dumps(analysis, indent=2, ensure_ascii=False))
    save_artifact(base / "sales_insights.txt", pretty_print_analysis(analysis))
    save_artifact(base / "sales_agent_prompt.txt", agent_prompt)

    # Print summary
    print(f"\n{DIVIDER}")
    print("  ANALYSIS SUMMARY")
    print(DIVIDER)
    if "executive_summary" in analysis:
        for line in textwrap.wrap(analysis["executive_summary"], width=63):
            print(f"  {line}")
    print(f"\n  Output folder: {base.resolve()}")
    print(DIVIDER)

    print("\n  FILES CREATED:")
    print("   transcript.txt              — raw transcript text")
    print("   transcript_timestamped.txt  — transcript with timestamps")
    print("   analysis.json               — structured JSON analysis")
    print("   sales_insights.txt          — human-readable insights report")
    print("   sales_agent_prompt.txt      — READY-TO-USE sales agent prompt")
    print(DIVIDER)

    # Print agent prompt preview
    print("\n  SALES AGENT PROMPT PREVIEW (first 600 chars):")
    print(DIVIDER)
    preview = agent_prompt[:600]
    for line in textwrap.wrap(preview, width=63):
        print(f"  {line}")
    print("  ...")
    print(DIVIDER)

    # Optional: launch interactive agent
    if launch_agent:
        print("\nLaunching interactive sales agent...")
        print("The agent will use the generated prompt. YOU play the prospect.\n")
        sales_agent = SalesAgent(agent_prompt, client, model=model)
        run_interactive_agent(sales_agent)

    return base


def run_interactive_mode(prompt_file: Path, api_key: str, model: str):
    """Load a previously saved agent prompt and run it interactively."""
    if not prompt_file.exists():
        print(f"ERROR: Prompt file not found: {prompt_file}")
        sys.exit(1)

    agent_prompt = prompt_file.read_text(encoding="utf-8").strip()
    if not agent_prompt:
        print("ERROR: Prompt file is empty.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print(f"\nLoaded prompt from: {prompt_file}")
    sales_agent = SalesAgent(agent_prompt, client, model=model)
    run_interactive_agent(sales_agent)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sales_analyzer",
        description=(
            "YouTube Sales Transcript Analyzer\n"
            "Extract sales insights from any YouTube video and generate\n"
            "a ready-to-use sales agent prompt powered by Claude AI.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Analyze a video and save artifacts
              python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

              # Analyze and immediately launch the interactive agent
              python main.py "https://youtu.be/VIDEO_ID" --agent

              # Load a previously generated prompt and run the agent
              python main.py --interactive ./sales_VIDEO_ID/sales_agent_prompt.txt

              # Set output directory and model
              python main.py URL --output ./my_analyses --model claude-opus-4-5
        """),
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube video URL to analyze",
    )
    parser.add_argument(
        "--interactive", "-i",
        metavar="PROMPT_FILE",
        help="Skip pipeline; load a saved agent prompt and run interactive mode",
    )
    parser.add_argument(
        "--agent", "-a",
        action="store_true",
        help="After analysis, launch the interactive sales agent",
    )
    parser.add_argument(
        "--output", "-o",
        default="./sales_outputs",
        metavar="DIR",
        help="Directory for output files (default: ./sales_outputs)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-opus-4-5",
        metavar="MODEL",
        help="Claude model to use (default: claude-opus-4-5)",
    )
    parser.add_argument(
        "--api-key", "-k",
        metavar="KEY",
        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var / .env file)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Resolve API key
    api_key = args.api_key or load_env_api_key()
    if not api_key:
        api_key = input("Enter your Anthropic API key: ").strip()
    if not api_key:
        print("ERROR: Anthropic API key is required.")
        sys.exit(1)

    # Interactive-only mode
    if args.interactive:
        run_interactive_mode(Path(args.interactive), api_key, args.model)
        return

    # Full pipeline mode
    url = args.url
    if not url:
        url = input("Enter YouTube video URL: ").strip()
    if not url:
        print("ERROR: A YouTube URL is required.")
        sys.exit(1)

    print(f"\n{DIVIDER}")
    print("  YOUTUBE SALES TRANSCRIPT ANALYZER")
    print(DIVIDER)
    print(f"  URL   : {url}")
    print(f"  Model : {args.model}")
    print(f"  Output: {Path(args.output).resolve()}")
    print(DIVIDER)

    run_pipeline(
        url=url,
        api_key=api_key,
        output_dir=Path(args.output),
        launch_agent=args.agent,
        model=args.model,
    )


if __name__ == "__main__":
    main()
