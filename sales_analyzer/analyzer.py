"""
Claude AI Sales Transcript Analyzer

Sends the video transcript to Claude and extracts a structured
breakdown of every sales insight embedded in the content.
"""

import json
import re
from typing import Union
import anthropic

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """You are a world-class sales coach and strategist with expertise in SPIN Selling,
Challenger Sale, MEDDIC/MEDDPICC, Solution Selling, Consultative Selling, and Sandler methodology.
You can dissect any sales training content and extract every actionable insight with surgical precision.
Your analysis powers AI sales agents that must perform at the highest level in live conversations."""

EXTRACTION_USER_TEMPLATE = """Analyze the following video transcript and extract EVERY sales insight it contains.
Be exhaustive and specific — include exact quotes, scripts, and examples from the transcript wherever possible.

TRANSCRIPT:
{transcript}

---

Return a JSON object with EXACTLY these keys (all values as strings or arrays of strings):

{{
  "video_topic": "One-sentence description of what this video is about",
  "sales_methodology": {{
    "primary_framework": "Main methodology/framework taught (SPIN, Challenger, MEDDIC, etc.)",
    "core_philosophy": "The overarching sales philosophy or mindset presented",
    "process_overview": "Step-by-step overview of the sales process shown"
  }},
  "key_techniques": [
    "Specific technique 1 with HOW to apply it",
    "Specific technique 2 with HOW to apply it"
  ],
  "discovery_questions": [
    "Exact discovery question 1",
    "Exact discovery question 2"
  ],
  "qualifying_criteria": [
    "Qualifying signal or criterion 1",
    "Qualifying signal or criterion 2"
  ],
  "pain_points_to_uncover": [
    "Pain point or problem area 1",
    "Pain point or problem area 2"
  ],
  "objection_handling": [
    {{
      "objection": "The exact objection",
      "response": "The recommended response or reframe",
      "follow_up": "What to say after the response"
    }}
  ],
  "value_propositions": [
    "Key value point 1 — how to articulate it",
    "Key value point 2 — how to articulate it"
  ],
  "closing_strategies": [
    "Closing technique 1 with example",
    "Closing technique 2 with example"
  ],
  "scripts_and_talk_tracks": [
    {{
      "stage": "Stage of conversation (e.g., opener, discovery, demo, close)",
      "script": "Exact script or talk track from the video"
    }}
  ],
  "buyer_psychology": [
    "Psychological insight 1 — how to leverage it",
    "Psychological insight 2 — how to leverage it"
  ],
  "buying_signals": [
    "Signal that a prospect is ready to buy 1",
    "Signal that a prospect is ready to buy 2"
  ],
  "follow_up_strategies": [
    "Follow-up strategy 1",
    "Follow-up strategy 2"
  ],
  "negotiation_tactics": [
    "Negotiation tactic 1",
    "Negotiation tactic 2"
  ],
  "rapport_and_trust_building": [
    "Trust-building technique 1",
    "Trust-building technique 2"
  ],
  "metrics_and_kpis": [
    "Key metric or KPI to track 1",
    "Key metric or KPI to track 2"
  ],
  "mindset_principles": [
    "Mental framework or attitude 1",
    "Mental framework or attitude 2"
  ],
  "case_studies_and_examples": [
    {{
      "situation": "The situation described",
      "approach": "What was done",
      "outcome": "The result or lesson"
    }}
  ],
  "common_mistakes_to_avoid": [
    "Mistake 1 and why it hurts sales",
    "Mistake 2 and why it hurts sales"
  ],
  "key_quotes": [
    "Memorable quote or principle from the video"
  ],
  "executive_summary": "3-5 sentence summary of the most critical takeaways from this video for a sales professional"
}}

Return ONLY valid JSON. No explanation outside the JSON block."""


def analyze_transcript(transcript_text: str, client: anthropic.Anthropic, model: str = "claude-opus-4-5") -> dict:
    """
    Send the transcript to Claude and extract structured sales insights.

    Returns a Python dict with the full analysis.
    """
    user_message = EXTRACTION_USER_TEMPLATE.format(transcript=transcript_text)

    response = client.messages.create(
        model=model,
        max_tokens=8096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract JSON block from surrounding text
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        # Fall back: return raw text wrapped in a dict
        return {"raw_analysis": raw, "parse_error": True}


def pretty_print_analysis(analysis: dict) -> str:
    """Return a human-readable summary of the extracted analysis."""
    if "parse_error" in analysis:
        return analysis.get("raw_analysis", "No analysis available.")

    lines = []

    def section(title: str, content: Union[str, list, dict]):
        lines.append(f"\n{'='*60}")
        lines.append(f"  {title}")
        lines.append('='*60)
        if isinstance(content, str):
            lines.append(content)
        elif isinstance(content, list):
            for i, item in enumerate(content, 1):
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"  [{i}] {k.upper()}: {v}")
                    lines.append("")
                else:
                    lines.append(f"  • {item}")
        elif isinstance(content, dict):
            for k, v in content.items():
                lines.append(f"  {k}: {v}")

    lines.append(f"\nVIDEO: {analysis.get('video_topic', 'N/A')}")

    if meth := analysis.get("sales_methodology"):
        section("SALES METHODOLOGY", meth)

    if kp := analysis.get("key_techniques"):
        section("KEY TECHNIQUES", kp)

    if dq := analysis.get("discovery_questions"):
        section("DISCOVERY QUESTIONS", dq)

    if oh := analysis.get("objection_handling"):
        section("OBJECTION HANDLING", oh)

    if cs := analysis.get("closing_strategies"):
        section("CLOSING STRATEGIES", cs)

    if st := analysis.get("scripts_and_talk_tracks"):
        section("SCRIPTS & TALK TRACKS", st)

    if ex := analysis.get("executive_summary"):
        section("EXECUTIVE SUMMARY", ex)

    return '\n'.join(lines)
