"""Probe the Google Maps actor on a vertical. Run: python -m tests.probe_maps "<search>" <n>"""
import json, os, sys
from datetime import timedelta
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
c = ApifyClient(os.environ["APIFY_API_TOKEN"])
actor = "compass/crawler-google-places"
build = c.actor(actor).default_build().get()
raw = build.actor_definition.input
inp = raw if isinstance(raw, dict) else raw.model_dump(by_alias=True)
print("input fields (subset):", [k for k in inp.get("properties", {}) if k in (
    "searchStringsArray","locationQuery","maxCrawledPlacesPerSearch","language","skipClosedPlaces","website","placeMinimumStars","scrapeContacts","scrapePlaceDetailPage")])

search, n = sys.argv[1], int(sys.argv[2])
run = c.actor(actor).call(
    run_input={"searchStringsArray": [search], "maxCrawledPlacesPerSearch": n, "language": "en", "skipClosedPlaces": True},
    timeout=timedelta(seconds=300), logger=None)
items = list(c.dataset(run.default_dataset_id).iterate_items())
Path(__file__).parent.joinpath("probe_output").mkdir(exist_ok=True)
Path(__file__).parent.joinpath("probe_output", "maps.json").write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
print("status", run.status, "| places", len(items), "| cost USD", getattr(run, "usage_total_usd", None))
print("keys:", sorted(items[0].keys())[:40] if items else None)
for i in items:
    print("-", i.get("title"), "|", i.get("categoryName"), "|", i.get("website"), "|", i.get("phone"), "|", i.get("reviewsCount"), "reviews |", i.get("totalScore"))
