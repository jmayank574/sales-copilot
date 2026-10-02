"""Print input schemas of the Apify actors. Run: python -m tests.inspect_actors"""
import json
import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
for name in ["harvestapi/linkedin-profile-scraper", "apify/website-content-crawler"]:
    build = c.actor(name).default_build().get()
    raw = build.actor_definition.input if getattr(build, "actor_definition", None) else None
    inp = raw if isinstance(raw, dict) else (raw.model_dump(by_alias=True) if raw is not None else {})
    print("==", name)
    for k, p in inp.get("properties", {}).items():
        print(" ", k, "|", p.get("type"), "| default:", str(p.get("default"))[:50], "|", p.get("enum") or "")
    print("  required:", inp.get("required"))
