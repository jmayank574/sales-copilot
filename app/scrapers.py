import os
import re
from datetime import timedelta

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_ACTOR = "harvestapi/linkedin-profile-scraper"
WEBSITE_ACTOR = "apify/website-content-crawler"
MAX_SITE_CHARS = 6000
TIMEOUT = timedelta(seconds=240)


def _client() -> ApifyClient:
    return ApifyClient(os.environ["APIFY_API_TOKEN"])


def clean(text: str | None) -> str:
    """Strip zero-width and control characters and collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"[​‌‍⁠﻿�]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def scrape_linkedin(url: str) -> dict:
    """Return a compact profile dict. Raises if the actor returns nothing."""
    c = _client()
    run = c.actor(LINKEDIN_ACTOR).call(run_input={"urls": [url]}, timeout=TIMEOUT, logger=None)
    items = list(c.dataset(run.default_dataset_id).iterate_items())
    if not items:
        raise RuntimeError("LinkedIn scraper returned no profile")
    p = items[0]
    positions = [
        f"{x.get('position') or ''} at {x.get('companyName') or ''}".strip()
        for x in (p.get("currentPosition") or [])
    ]
    experience = [
        f"{x.get('position') or ''} at {x.get('companyName') or ''}".strip()
        for x in (p.get("experience") or [])[:4]
    ]
    return {
        "name": clean(f"{p.get('firstName', '')} {p.get('lastName', '')}"),
        "headline": clean(p.get("headline")),
        "about": clean(p.get("about"))[:1500],
        "location": clean((p.get("location") or {}).get("linkedinText")) if isinstance(p.get("location"), dict) else clean(str(p.get("location") or "")),
        "followers": p.get("followerCount"),
        "current_positions": positions,
        "experience": experience,
        "top_skills": [clean(s) for s in (p.get("topSkills") or [])][:8] if isinstance(p.get("topSkills"), list) else clean(str(p.get("topSkills") or "")),
    }


def _crawl(url: str, crawler_type: str) -> str:
    c = _client()
    run = c.actor(WEBSITE_ACTOR).call(
        run_input={
            "startUrls": [{"url": url}],
            "maxCrawlPages": 3,
            "maxCrawlDepth": 1,
            "crawlerType": crawler_type,
            "proxyConfiguration": {"useApifyProxy": True},
        },
        timeout=TIMEOUT,
        logger=None,
    )
    items = c.dataset(run.default_dataset_id).iterate_items()
    return clean(" ".join(i.get("text") or "" for i in items))


def scrape_website(url: str) -> str:
    """Cheap HTML crawl first; fall back to a browser crawl if the page is empty."""
    text = _crawl(url, "cheerio")
    if len(text) < 200:
        text = _crawl(url, "playwright:adaptive")
    if not text:
        raise RuntimeError("Website crawler returned no text")
    return text[:MAX_SITE_CHARS]
