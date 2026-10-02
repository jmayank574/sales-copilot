import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app import enrich, scrapers, sheets, typeform

load_dotenv()
log = logging.getLogger("copilot")
logging.basicConfig(level=logging.INFO)
app = FastAPI()


def process_lead(lead: dict) -> str:
    """Scrape, enrich and write one lead. Returns the Status written to the sheet."""
    errors = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        li_f = pool.submit(scrapers.scrape_linkedin, lead["linkedin"]) if lead["linkedin"] else None
        web_f = pool.submit(scrapers.scrape_website, lead["website"]) if lead["website"] else None
        linkedin = website = None
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
        result = enrich.enrich(lead, linkedin, website)
        row.update(
            {
                "Niche/Industry": result["niche"],
                "Primary Service": result["primary_service"],
                "ICP Fit Score (1-10)": result["icp_score"],
                "ICP Fit Reason": result["icp_reason"],
                "Personalized Icebreaker": result["icebreaker"],
            }
        )
        row["Status"] = "partial: " + "; ".join(errors) if errors else "ok"
    except Exception as e:
        log.exception("Enrichment failed")
        row["Status"] = "error: " + "; ".join(errors + [str(e)])[:300]

    if not sheets.append_lead(row):
        log.info("Duplicate email %s skipped", lead["email"])
        return "duplicate"
    log.info("Wrote %s with status %s", lead["email"], row["Status"])
    return row["Status"]


@app.get("/health")
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
