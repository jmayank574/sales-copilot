"""Run each scraper once on a public test lead and dump raw output. Run: python -m tests.probe_scrapers"""
import json
import os
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
out = Path(__file__).parent / "probe_output"
out.mkdir(exist_ok=True)

LINKEDIN = "https://www.linkedin.com/in/williamhgates/"
WEBSITE = "https://www.gatesnotes.com/"

RUNS = {
    "profile": ("harvestapi/linkedin-profile-scraper", {"urls": [LINKEDIN]}),
    "posts": ("harvestapi/linkedin-profile-posts", {"targetUrls": [LINKEDIN], "maxPosts": 5}),
    "website": (
        "apify/website-content-crawler",
        {
            "startUrls": [{"url": WEBSITE}],
            "maxCrawlPages": 3,
            "maxCrawlDepth": 1,
            "crawlerType": "cheerio",
            "proxyConfiguration": {"useApifyProxy": True},
        },
    ),
}

for key, (actor, run_input) in RUNS.items():
    print(f"--- {key}: {actor}")
    try:
        run = c.actor(actor).call(run_input=run_input, timeout=__import__("datetime").timedelta(seconds=240))
        items = list(c.dataset(run.default_dataset_id).iterate_items())
        (out / f"{key}.json").write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        print(f"  status={run.status} items={len(items)}")
        if items:
            print("  keys:", sorted(items[0].keys()))
    except Exception as e:
        print("  FAILED:", type(e).__name__, str(e)[:300])
