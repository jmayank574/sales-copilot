import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from app import scoring

load_dotenv()

CONTEXT_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "fernstone_context.md"

RULES = """You assess one inbound lead for Fernstone using only the scraped LinkedIn profile and company website text provided. Either source may be missing.

For EACH factor, choose exactly one level from that factor's allowed levels and give:
- evidence: a short quote or concrete fact taken from the provided data. If you cannot point to something in the data, the level must be "unknown" and evidence must be empty.
- confidence: high (stated directly in the data), medium (reasonable reading of the data), or low (thin).

Rules:
- You do NOT produce a total score or priority. Code computes those.
- Never infer a fact from an industry stereotype alone. Evidence must come from the data.
- Do not treat submitting the form as a buying trigger.
- Facts tagged [assumption] in the Fernstone context are drafts, not confirmed. Apply them as the working definition but do not state them as Fernstone facts in your evidence.
- Also return company_summary (1-2 plain sentences on what the business does, from the data only), niche (a few words), and primary_service (one short phrase)."""


def _system_prompt(rubric: dict) -> str:
    parts = [RULES, "\n# Fernstone context\n", CONTEXT_PATH.read_text(encoding="utf-8"), "\n# Factors and allowed levels\n"]
    for f in scoring.enabled_factors(rubric):
        parts.append(f"## {f['key']} ({f['label']})\n{f['guidance']}")
        for name, lv in f["levels"].items():
            parts.append(f"- {name}: {lv['definition']}")
        parts.append("")
    return "\n".join(parts)


def _tool(rubric: dict) -> dict:
    factor_props = {
        f["key"]: {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": list(f["levels"].keys())},
                "evidence": {"type": "string"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": ["level", "evidence", "confidence"],
        }
        for f in scoring.enabled_factors(rubric)
    }
    props = {
        **factor_props,
        "company_summary": {"type": "string"},
        "niche": {"type": "string"},
        "primary_service": {"type": "string"},
    }
    return {
        "name": "record_assessment",
        "description": "Record per-factor judgments for this lead.",
        "input_schema": {"type": "object", "properties": props, "required": list(props.keys())},
    }


OUTBOUND_NOTE = (
    "This is an OUTBOUND prospect, not a form submitter. lead_name is the company name. The contact is whoever the "
    "company website explicitly names as owner, founder, president or CEO. Judge decision_maker from that stated "
    "leadership; if the site names none, use unknown. Use the google_maps_listing only for facts it contains. "
    "The Maps review count is an indirect size signal only (a large count suggests an established client base, "
    "not headcount); cite it as indirect evidence if you use it. A Maps address that is an apartment suggests a "
    "home-based business."
)

HYPOTHESIS_NOTE = (
    "VERTICAL UNDER TEST: {hypothesis} This vertical is NOT in Fernstone's published list; it is a hypothesis being "
    "tested. For target_industry, judge fit to THIS vertical definition instead of the published list: strong = clearly "
    "matches the definition; partial = mixed or unclear; none = clearly outside it. In the evidence, say that it is a "
    "hypothesis outside the published verticals."
)


def assess(
    lead: dict,
    linkedin: dict | None,
    website_text: str | None,
    rubric: dict | None = None,
    extra: dict | None = None,
    mode: str = "inbound",
    hypothesis: str | None = None,
) -> dict:
    """Return {'judgments', 'company_summary', 'niche', 'primary_service', 'result'} where
    result is the code-computed score from app.scoring.compute."""
    rubric = rubric or scoring.load_rubric()
    payload = {
        "lead_name": lead.get("name"),
        "linkedin_profile": linkedin or "NOT AVAILABLE",
        "company_website_text": website_text or "NOT AVAILABLE",
    }
    if extra:
        payload["google_maps_listing"] = extra
    if mode == "outbound":
        payload["mode"] = OUTBOUND_NOTE
        if hypothesis:
            payload["vertical_under_test"] = HYPOTHESIS_NOTE.format(hypothesis=hypothesis)
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=1800,
        system=_system_prompt(rubric),
        tools=[_tool(rubric)],
        messages=[
            {
                "role": "user",
                "content": "Call record_assessment for this lead.\n" + json.dumps(payload, ensure_ascii=False),
            }
        ],
    )
    block = next((b for b in resp.content if b.type == "tool_use"), None)
    if block is None:
        raise RuntimeError("Claude did not return a tool call")
    out = dict(block.input)
    judgments = {k: out.pop(k) for k in [f["key"] for f in scoring.enabled_factors(rubric)] if k in out}
    context = {"linkedin_available": bool(linkedin), "contact_source": "form" if mode == "inbound" else "company_website"}
    result = scoring.compute(judgments, rubric, context)
    return {**out, "judgments": judgments, "result": result}
