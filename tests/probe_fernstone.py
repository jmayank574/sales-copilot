"""Crawl fernstone.com for prompt-writing context. Run: python -m tests.probe_fernstone"""
import os
from datetime import timedelta

from apify_client import ApifyClient
from dotenv import load_dotenv

from app.scrapers import clean

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
run = c.actor("apify/website-content-crawler").call(
    run_input={"startUrls": [{"url": "https://fernstone.com/"}], "maxCrawlPages": 8, "maxCrawlDepth": 1,
               "crawlerType": "playwright:adaptive", "proxyConfiguration": {"useApifyProxy": True}},
    timeout=timedelta(seconds=240), logger=None)
for i in c.dataset(run.default_dataset_id).iterate_items():
    print("##", i["url"], len(i["text"]))
    print(clean(i["text"])[:1200])
