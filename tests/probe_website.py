"""Retry website crawl with browser crawler. Run: python -m tests.probe_website"""
import os
from datetime import timedelta

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
for url in ["https://www.gatesnotes.com/", "https://www.gatesfoundation.org/"]:
    run = c.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": url}],
            "maxCrawlPages": 3,
            "maxCrawlDepth": 1,
            "crawlerType": "playwright:adaptive",
            "proxyConfiguration": {"useApifyProxy": True},
        },
        timeout=timedelta(seconds=240),
        logger=None,
    )
    items = list(c.dataset(run.default_dataset_id).iterate_items())
    print(url, "status", run.status, "pages", len(items), "text chars", [len(i["text"]) for i in items])
    if items and items[0]["text"]:
        print("  head:", items[0]["text"][:200].replace("\n", " "))
