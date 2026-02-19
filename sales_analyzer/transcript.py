"""
YouTube Transcript Extraction Module

Fetches transcripts from YouTube videos using youtube-transcript-api v1.x.
Supports multiple languages and automatic translation to English.
"""

import re
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.

    Supports:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/shorts/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # Last resort: treat as raw video ID if exactly 11 chars
    stripped = url.strip()
    if re.match(r'^[a-zA-Z0-9_-]{11}$', stripped):
        return stripped
    return None


def _snippets_to_list(fetched) -> list:
    """Convert FetchedTranscript snippets to plain dicts for uniform handling."""
    return [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in fetched
    ]


def fetch_transcript(video_id: str, preferred_langs: Optional[list] = None) -> dict:
    """
    Fetch the full transcript for a YouTube video.

    Returns a dict with:
      - text: full concatenated transcript text
      - segments: list of {text, start, duration}
      - language: detected language code
      - was_translated: whether an auto-translation was used
    """
    if preferred_langs is None:
        preferred_langs = ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU']

    api = YouTubeTranscriptApi()

    try:
        # Fast path — fetch directly in a preferred language
        try:
            fetched = api.fetch(video_id, languages=preferred_langs)
            segments = _snippets_to_list(fetched)
            return {
                'text': ' '.join(seg['text'] for seg in segments),
                'segments': segments,
                'language': 'en',
                'was_translated': False,
            }
        except NoTranscriptFound:
            pass

        # List all available transcripts
        transcript_list = api.list(video_id)

        # Prefer manual over auto-generated (manual is more accurate)
        try:
            transcript = transcript_list.find_manually_created_transcript(preferred_langs)
            was_translated = False
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(preferred_langs)
                was_translated = False
            except NoTranscriptFound:
                # Nothing in English — grab whatever exists and translate
                all_transcripts = list(transcript_list)
                if not all_transcripts:
                    raise RuntimeError("No transcripts are available for this video.")
                transcript = all_transcripts[0]
                if transcript.language_code not in preferred_langs:
                    transcript = transcript.translate('en')
                    was_translated = True
                else:
                    was_translated = False

        fetched = transcript.fetch()
        segments = _snippets_to_list(fetched)
        return {
            'text': ' '.join(seg['text'] for seg in segments),
            'segments': segments,
            'language': transcript.language_code,
            'was_translated': was_translated,
        }

    except TranscriptsDisabled:
        raise RuntimeError(
            "Transcripts are disabled for this video. "
            "The video owner has turned off subtitles/captions."
        )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch transcript: {exc}") from exc


def format_transcript_with_timestamps(segments: list) -> str:
    """Return a timestamped transcript string for readability."""
    lines = []
    for seg in segments:
        start = int(seg['start'])
        minutes, seconds = divmod(start, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        else:
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text']}")
    return '\n'.join(lines)
