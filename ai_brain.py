import anthropic
import json
import re
from models import Lead, ScoredLead, LeadOutput
from config import ICP, ANTHROPIC_API_KEY
import logging

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SCORE_SYSTEM_PROMPT = """You are a lead qualification expert for a senior web development agency.
Your job is to score incoming project leads against an Ideal Customer Profile (ICP).

You must respond with ONLY a valid JSON object — no markdown, no explanation outside the JSON.

JSON schema:
{
  "score": float between 0.0 and 1.0,
  "reasoning": "2-3 sentence explanation",
  "key_signals": ["signal1", "signal2", "signal3"]
}

Scoring guide:
- 0.9–1.0: Perfect fit. High budget, custom technical work, clear scope
- 0.7–0.89: Strong fit. Good budget, some custom work needed
- 0.5–0.69: Moderate. Budget or scope is unclear
- 0.0–0.49: Poor fit. Low budget, templated work, or mismatched signals
"""


PITCH_SYSTEM_PROMPT = """You are a senior web developer writing a personalized pitch response 
on Bark.com. Write in first person, warm but professional tone.

CRITICAL RULES:
1. Write EXACTLY 3 paragraphs
2. Reference AT LEAST 2 specific details from the lead (project specifics, location, budget context, 
   technology mentioned, timeline, business type)
3. Do NOT use generic filler like "I noticed you're looking for..." 
4. End with a clear call to action
5. Keep total length under 300 words
6. Sound like a human expert, not a template
"""


def score_lead(lead: Lead) -> ScoredLead:
    """Send lead to Claude for ICP scoring."""
    user_message = f"""
{ICP.to_prompt_context()}

LEAD TO EVALUATE:
Title: {lead.title}
Description: {lead.description}
Budget: {lead.budget}
Location: {lead.location}

Score this lead against the ICP.
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=SCORE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"```json|```", "", raw).strip()
    parsed = json.loads(raw)

    return ScoredLead(
        lead=lead,
        score=float(parsed["score"]),
        reasoning=parsed["reasoning"],
        key_signals=parsed.get("key_signals", []),
    )


def generate_pitch(scored_lead: ScoredLead) -> str:
    """Generate a personalized 3-paragraph pitch for high-scoring leads."""
    lead = scored_lead.lead
    user_message = f"""
Write a personalized pitch response for this Bark.com project request.

PROJECT DETAILS:
Title: {lead.title}
Description: {lead.description}
Budget: {lead.budget}
Location: {lead.location}

Key signals identified: {', '.join(scored_lead.key_signals)}

Remember: Reference at least 2 specific details from the description above.
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=PITCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text.strip()


def process_lead(lead: Lead) -> LeadOutput:
    """Full pipeline: score → conditionally generate pitch."""
    scored = score_lead(lead)
    logger.info(f"Lead '{lead.title[:40]}...' scored {scored.score:.2f}")

    pitch = None
    if scored.score > 0.8:
        logger.info(f"Score {scored.score:.2f} ≥ 0.8 — generating pitch...")
        pitch = generate_pitch(scored)

    return LeadOutput(scored_lead=scored, pitch=pitch)