"""One-off outbound vertical list: Google Maps -> website -> same scoring engine -> ranked tab.

Run: python -m app.vertical "commercial cleaning services New York NY" --n 30 --tab "Vertical: NYC commercial cleaning"
Nothing is sent. Output is a ranked call list with prep notes for a human caller."""
import argparse
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from apify_client import ApifyClient
from dotenv import load_dotenv

from app import assess, routing, scrapers, sheets
from app import brief as brief_mod

load_dotenv()
log = logging.getLogger("copilot.vertical")
MAPS_ACTOR = "compass/crawler-google-places"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
OUTBOUND_ROUTING = routing.load_routing(routing.ROUTING_PATH.parent / "routing_outbound.json")
ROUTE_ORDER = {"Call first": 0, "Second wave": 1, "Research first": 2, "Skip": 3}

HEADERS = [
    "Rank", "Company", "Website", "Phone", "Address", "Google Rating", "Reviews",
    "Owner (stated on site)", "Owner Title", "Find Contact",
    "Fit Score (0-100)", "Priority", "Confidence", "Route", "Next Action",
    "Why This Company", "Cold-call Opener", "Discovery Questions", "Score Evidence", "Missing Info", "Status",
]
WRAP = ["Next Action", "Why This Company", "Cold-call Opener", "Discovery Questions", "Score Evidence", "Missing Info"]


def clean_url(url: str) -> str:
    p = urlparse(url)
    return (f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")) or url


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def maps_search(search: str, n: int) -> list[dict]:
    c = ApifyClient(os.environ["APIFY_API_TOKEN"])
    run = c.actor(MAPS_ACTOR).call(
        run_input={"searchStringsArray": [search], "maxCrawledPlacesPerSearch": n, "language": "en", "skipClosedPlaces": True},
        timeout=timedelta(seconds=600),
        logger=None,
    )
    return list(c.dataset(run.default_dataset_id).iterate_items())


def _contact_link(owner: str, company: str) -> str:
    who = owner or "owner OR president"
    return "https://www.google.com/search?q=" + quote_plus(f"{who} {company} New York linkedin")


def _fmt_evidence(result: dict) -> str:
    return "\n".join(
        f"{x['label']}: {x['level']} ({x['points']:g}/{x['max_points']}, {x['confidence']})"
        + (f" - {x['evidence']}" if x["evidence"] else "")
        + (f" [{x['note']}]" if x["note"] else "")
        for x in result["breakdown"]
    )


def process(place: dict, hypothesis: str | None = None) -> dict:
    name = place.get("title") or "Unknown"
    site = clean_url(place["website"])
    maps = {
        "name": name,
        "category": place.get("categoryName"),
        "address": place.get("address"),
        "rating": place.get("totalScore"),
        "reviews": place.get("reviewsCount"),
    }
    row = {
        "Company": name,
        "Website": site,
        "Phone": place.get("phone") or "",
        "Address": place.get("address") or "",
        "Google Rating": place.get("totalScore") or "",
        "Reviews": place.get("reviewsCount") or "",
        "_score": -1,
        "_route": "Research first",
    }
    try:
        text = scrapers.scrape_website(site)
        a = assess.assess({"name": name}, None, text, extra=maps, mode="outbound", hypothesis=hypothesis)
        r = a["result"]
        route = routing.decide(r, no_data=False, routing=OUTBOUND_ROUTING)
        b = brief_mod.generate_outbound(name, a, route, maps, text)
        owner = (b.get("owner_name") or "").strip()
        row.update(
            {
                "Owner (stated on site)": owner,
                "Owner Title": (b.get("owner_title") or "").strip(),
                "Find Contact": _contact_link(owner, name),
                "Fit Score (0-100)": r["score"],
                "Priority": r["priority"],
                "Confidence": r["confidence"],
                "Route": route["route"],
                "Next Action": route["action"],
                "Why This Company": b["why_this_company"],
                "Cold-call Opener": b["opener"],
                "Discovery Questions": "\n".join(f"{i}) {x}" for i, x in enumerate(b["discovery_questions"], 1)),
                "Score Evidence": _fmt_evidence(r),
                "Missing Info": "; ".join(r["missing"]),
                "Status": "ok",
                "_score": r["score"],
                "_route": route["route"],
            }
        )
    except Exception as e:
        log.exception("Failed for %s", name)
        route = routing.decide(None, no_data=True, routing=OUTBOUND_ROUTING)
        row.update(
            {
                "Route": route["route"],
                "Next Action": route["action"],
                "Status": f"error: {e}"[:200],
                "Find Contact": _contact_link("", name),
            }
        )
    return row


def run(search: str, n: int, tab: str, workers: int = 4, hypothesis: str | None = None) -> None:
    places = maps_search(search, n)
    seen, todo = set(), []
    for p in places:
        if not p.get("website"):
            continue
        d = domain(p["website"])
        if d in seen:
            continue
        seen.add(d)
        todo.append(p)
    print(f"{len(places)} listings from Maps, {len(todo)} unique companies with a website")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda p: process(p, hypothesis), todo))
    # Ties are common because evidence is thin; break them by Google review volume (an indirect size signal).
    rows.sort(key=lambda r: (ROUTE_ORDER.get(r["_route"], 9), -r["_score"], -(int(r["Reviews"]) if str(r["Reviews"]).isdigit() else 0)))
    for i, r in enumerate(rows, 1):
        r["Rank"] = i
    table = [[r.get(h, "") for h in HEADERS] for r in rows]
    # Save locally first so a failed sheet write never throws away paid scraping and model calls.
    CACHE_DIR.mkdir(exist_ok=True)
    saved = CACHE_DIR / "vertical_last_run.json"
    saved.write_text(json.dumps({"tab": tab, "table": table}), encoding="utf-8")
    print("results saved locally:", saved)
    url = sheets.write_table(tab, HEADERS, table, WRAP)
    by_route = {}
    for r in rows:
        by_route[r["_route"]] = by_route.get(r["_route"], 0) + 1
    print("routes:", by_route)
    print("tab:", url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("search")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--tab", default="Vertical list")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--hypothesis", default=None, help="definition of the vertical under test, used to judge industry fit")
    ap.add_argument("--from-saved", action="store_true", help="write the last saved run to the sheet without re-running")
    args = ap.parse_args()
    if args.from_saved:
        saved = json.loads((CACHE_DIR / "vertical_last_run.json").read_text(encoding="utf-8"))
        print("tab:", sheets.write_table(saved["tab"], HEADERS, saved["table"], WRAP))
    else:
        run(args.search, args.n, args.tab, args.workers, args.hypothesis)
