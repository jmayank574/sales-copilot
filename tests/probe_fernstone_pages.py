"""Crawl Fernstone's Verticals/Carriers/Platform pages. Run: python -m tests.probe_fernstone_pages"""
import os
from datetime import timedelta
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

from app.scrapers import clean

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
urls = ["https://fernstone.com/"]
run = c.actor("apify/website-content-crawler").call(
    run_input={"startUrls": [{"url": u} for u in urls], "maxCrawlPages": 12, "maxCrawlDepth": 0,
               "crawlerType": "playwright:adaptive", "proxyConfiguration": {"useApifyProxy": True}},
    timeout=timedelta(seconds=300), logger=None)
out = []
for i in c.dataset(run.default_dataset_id).iterate_items():
    t = clean(i["text"])
    out.append(f"## {i['url']} ({len(t)} chars)\n{t}\n")
Path("docs/fernstone_site_extract.md").write_text("\n".join(out), encoding="utf-8")
for block in out:
    print(block)
    print()
