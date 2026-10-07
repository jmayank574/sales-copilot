import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app import assess, routing, scrapers, sheets, typeform
from app import brief as brief_mod

load_dotenv()
log = logging.getLogger("copilot")
logging.basicConfig(level=logging.INFO)
app = FastAPI()


def _fmt_evidence(result: dict) -> str:
    return "\n".join(
        f"{b['label']}: {b['level']} ({b['points']:g}/{b['max_points']}, {b['confidence']})"
        + (f" - {b['evidence']}" if b["evidence"] else "")
        + (f" [{b['note']}]" if b["note"] else "")
        for b in result["breakdown"]
    )


def _fmt_brief(brief: dict) -> dict:
    return {
        "Personalized Icebreaker": brief["icebreaker"],
        "Discovery Questions": "\n".join(f"{i}) {q}" for i, q in enumerate(brief["discovery_questions"], 1)),
        "Likely Insurance Needs (to confirm)": "\n".join(f"{n['coverage']}: {n['why']}" for n in brief["likely_needs"]),
        "Likely Objections & Replies": "\n\n".join(
            f"\"{o['objection']}\"\nAsk: {o['clarifying_question']}\nReply: {o['reply']}"
            for o in brief["likely_objections"]
        ),
        "Follow-up Email Draft": f"Subject: {brief['followup_subject']}\n\n{brief['followup_body']}",
        "_next_action": brief["next_action"],
    }


def _scrape(lead: dict) -> tuple[dict | None, str | None, list[str]]:
    errors = []
    linkedin = website = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        li_f = pool.submit(scrapers.scrape_linkedin, lead["linkedin"]) if lead["linkedin"] else None
        web_f = pool.submit(scrapers.scrape_website, lead["website"]) if lead["website"] else None
        for name, fut in (("LinkedIn", li_f), ("Website", web_f)):
            if fut is None:
                errors.append(f"{name}: no URL")
                continue
            try:
                result = fut.result()
                if name == "LinkedIn":
                    linkedin = result
                else:
                    website = result
            except Exception as e:
                log.exception("%s scrape failed", name)
                errors.append(f"{name}: {e}")
    return linkedin, website, errors


def process_lead(lead: dict) -> str:
    """Scrape, assess, route, brief and write one lead. Returns the Status written to the sheet."""
    linkedin, website, errors = _scrape(lead)
    row = {
        "Full Name": lead["name"],
        "Email": lead["email"],
        "Phone Number": lead["phone"],
        "Company Website": lead["website"],
        "LinkedIn": lead["linkedin"],
        "Received At": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    try:
        if linkedin is None and website is None:
            raise RuntimeError("No scraped data available")
        assessment = assess.assess(lead, linkedin, website)
        r = assessment["result"]
        route = routing.decide(r, no_data=False)
        row.update(
            {
                "Niche/Industry": assessment["niche"],
                "Primary Service": assessment["primary_service"],
                "Company Summary": assessment["company_summary"],
                "Fit Score (0-100)": r["score"],
                "Priority": r["priority"],
                "Confidence": r["confidence"],
                "Route": route["route"],
                "Next Action": route["action"],
                "Score Evidence": _fmt_evidence(r),
                "Missing Info": "; ".join(r["missing"]),
            }
        )
        if route["rule"] != "low":
            try:
                brief = _fmt_brief(brief_mod.generate(lead, assessment, route, linkedin, website))
                row["Next Action"] = f"{route['action']}\n\nRep: {brief.pop('_next_action')}"
                row.update(brief)
            except Exception as e:
                log.exception("Brief generation failed")
                errors.append(f"Brief: {e}")
        row["Status"] = "partial: " + "; ".join(errors)[:300] if errors else "ok"
    except Exception as e:
        log.exception("Assessment failed")
        route = routing.decide(None, no_data=True)
        row.update({"Route": route["route"], "Next Action": route["action"]})
        row["Status"] = "error: " + "; ".join(errors + [str(e)])[:300]

    if not sheets.append_lead(row):
        log.info("Duplicate email %s skipped", lead["email"])
        return "duplicate"
    log.info("Wrote %s with status %s", lead["email"], row["Status"])
    return row["Status"]


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    secret = os.environ.get("TYPEFORM_WEBHOOK_SECRET", "")
    if secret:
        if not typeform.verify_signature(raw, request.headers.get("Typeform-Signature"), secret):
            raise HTTPException(status_code=401, detail="bad signature")
    else:
        log.warning("TYPEFORM_WEBHOOK_SECRET not set: signature check skipped")
    lead = typeform.parse_lead(await request.json())
    if not lead["email"]:
        raise HTTPException(status_code=422, detail="no email in submission")
    background.add_task(process_lead, lead)
    return {"received": True}
