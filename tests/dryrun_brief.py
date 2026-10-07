"""Dry run assess + routing + brief on cached/scraped data; prints icebreaker and follow-up. Writes NOTHING.
Run: python -m tests.dryrun_brief adam frey roehl"""
import json
import sys

from app import assess, brief, routing, scrapers
from tests.dryrun_assess import CACHE, LEADS, cached

for key in sys.argv[1:]:
    lead = LEADS[key]
    li = cached(f"{key}_li", scrapers.scrape_linkedin, lead["linkedin"]) if lead["linkedin"] else None
    web = cached(f"{key}_web", scrapers.scrape_website, lead["website"])
    a = assess.assess(lead, li, web)
    route = routing.decide(a["result"], no_data=False)
    b = brief.generate(lead, a, route, li, web)
    print(f"\n=== {lead['name']} | score {a['result']['score']} {a['result']['priority']} | {route['route']}")
    print("ICEBREAKER:", b["icebreaker"], f"({len(b['icebreaker'].split())} words)")
    print("EMAIL SUBJECT:", b["followup_subject"])
    print("EMAIL BODY:", b["followup_body"], f"({len(b['followup_body'].split())} words)")
