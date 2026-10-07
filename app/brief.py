import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

TOOL = {
    "name": "record_brief",
    "description": "Record the sales brief for the rep.",
    "input_schema": {
        "type": "object",
        "properties": {
            "icebreaker": {"type": "string"},
            "discovery_questions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
            "likely_needs": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {"coverage": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["coverage", "why"],
                },
            },
            "likely_objections": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "objection": {"type": "string"},
                        "clarifying_question": {"type": "string"},
                        "reply": {"type": "string"},
                    },
                    "required": ["objection", "clarifying_question", "reply"],
                },
            },
            "next_action": {"type": "string"},
            "followup_subject": {"type": "string"},
            "followup_body": {"type": "string"},
        },
        "required": [
            "icebreaker", "discovery_questions", "likely_needs", "likely_objections",
            "next_action", "followup_subject", "followup_body",
        ],
    },
}


def _system_prompt() -> str:
    files = ["brief_guidelines.md", "fernstone_context.md", "objections.md"]
    return "You write the sales brief for one inbound lead, following the guidelines below exactly.\n\n" + "\n\n---\n\n".join(
        (KNOWLEDGE / f).read_text(encoding="utf-8") for f in files
    )


def generate(lead: dict, assessment: dict, route: dict, linkedin: dict | None, website_text: str | None) -> dict:
    r = assessment["result"]
    payload = {
        "lead_name": lead.get("name"),
        "company_summary": assessment.get("company_summary"),
        "niche": assessment.get("niche"),
        "primary_service": assessment.get("primary_service"),
        "score": r["score"],
        "priority": r["priority"],
        "confidence": r["confidence"],
        "missing_information": r["missing"],
        "routing_decision": route,
        "factor_evidence": [
            {"factor": b["label"], "level": b["level"], "evidence": b["evidence"]} for b in r["breakdown"]
        ],
        "linkedin_profile": linkedin or "NOT AVAILABLE",
        "company_website_text": website_text or "NOT AVAILABLE",
    }
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=2500,
        system=_system_prompt(),
        tools=[TOOL],
        messages=[
            {"role": "user", "content": "Call record_brief for this lead.\n" + json.dumps(payload, ensure_ascii=False)}
        ],
    )
    block = next((b for b in resp.content if b.type == "tool_use"), None)
    if block is None:
        raise RuntimeError("Claude did not return a tool call")
    return dict(block.input)
