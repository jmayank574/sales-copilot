import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You qualify inbound leads for Fernstone, a commercial insurance brokerage for businesses ("insurance for businesses that move fast"). Fernstone places business coverage (e.g. general liability, commercial auto, workers' comp, property) with carriers, and offers a platform for COIs, claims, policies and renewals. It earns nothing unless it places a policy.

Fernstone says it is a good fit for businesses that: want to save money without sacrificing coverage; know their business inside and out; take pride in running a strong, well-managed organization; and want a straightforward broker relationship. It is NOT a fit for people who want the fastest quote regardless of price or accuracy, won't share meaningful business details, or won't give underwriters the information they need.

You receive scraped LinkedIn profile data and/or company website text for one lead. Either source may be missing. Use only what is provided and never invent facts.

Return via the tool:
- niche: the lead's industry in a few words.
- primary_service: what the lead's business sells or does, in one short phrase.
- icp_score: integer 1-10 for how likely this is a real, insurable business buyer for Fernstone.
  9-10: an established operating business (real operations, employees, vehicles, locations or contracts) with a decision-maker (owner, founder, CEO, CFO, ops head) as the contact, in an industry that needs commercial coverage.
  6-8: likely a real business but details are thin, or the contact is not clearly the decision-maker.
  3-5: small or unclear business, solo freelancer with little insurable exposure, or the contact is far from buying decisions.
  1-2: not a business buyer (individual, student, large enterprise with its own risk team, insurance competitor) or not enough information to judge.
- icp_reason: 1-2 sentences citing specific evidence from the data. State which source was missing if any.
- icebreaker: what a sales rep says in the first 10 seconds of a call. Write it like a young, friendly peer talking to another founder, not a salesperson. Rules:
  * 1-2 short sentences, under 40 words, casual spoken English (contractions are fine).
  * Anchor it on one concrete, specific detail about their business or role from the data (what they do, where they operate, how they've grown). Never use a generic opener.
  * Banned: "I came across your profile", "I was impressed", "I hope you're doing well", "passionate", "thought leader", "inspiring", and any compliment that could apply to anyone.
  * End with a light, genuine question about their business. No pitch, and do not mention insurance products or pricing yet.
  * Example of the tone (do not reuse): "Saw you've got a fleet running out of three depots now. How's the growth been on the logistics side?" """

TOOL = {
    "name": "record_lead_enrichment",
    "description": "Record the enrichment result for this lead.",
    "input_schema": {
        "type": "object",
        "properties": {
            "niche": {"type": "string"},
            "primary_service": {"type": "string"},
            "icp_score": {"type": "integer", "minimum": 1, "maximum": 10},
            "icp_reason": {"type": "string"},
            "icebreaker": {"type": "string"},
        },
        "required": ["niche", "primary_service", "icp_score", "icp_reason", "icebreaker"],
    },
}


def enrich(lead: dict, linkedin: dict | None, website_text: str | None) -> dict:
    payload = {
        "lead_name": lead.get("name"),
        "linkedin_profile": linkedin or "NOT AVAILABLE",
        "company_website_text": website_text or "NOT AVAILABLE",
    }
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=800,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        messages=[
            {
                "role": "user",
                "content": "Call record_lead_enrichment for this lead.\n" + json.dumps(payload, ensure_ascii=False),
            }
        ],
    )
    block = next((b for b in resp.content if b.type == "tool_use"), None)
    if block is None:
        raise RuntimeError("Claude did not return a tool call")
    result = dict(block.input)
    result["icp_score"] = max(1, min(10, int(result["icp_score"])))
    return result
