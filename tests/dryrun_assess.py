"""Dry run: scrape (cached), assess, score. Writes NOTHING to the sheet.
Run: python -m tests.dryrun_assess [name ...]   (names from LEADS below)"""
import json
import sys
from pathlib import Path

from app import assess, scrapers

CACHE = Path(__file__).resolve().parent.parent / ".cache"
CACHE.mkdir(exist_ok=True)

LEADS = {
    "adam": {"name": "Adam Levine", "website": "https://www.capitolfire.com/",
             "linkedin": "https://www.linkedin.com/in/adam-levine-cfs/"},
    "gates": {"name": "Bill Gates", "website": "https://www.gatesnotes.com/",
              "linkedin": "https://www.linkedin.com/in/williamhgates/"},
}


def cached(key, fn, arg):
    p = CACHE / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    try:
        v = fn(arg)
    except Exception as e:
        print(f"  ! {key} failed: {e}")
        v = None
    p.write_text(json.dumps(v), encoding="utf-8")
    return v


for name in sys.argv[1:] or LEADS:
    lead = LEADS[name]
    li = cached(f"{name}_li", scrapers.scrape_linkedin, lead["linkedin"])
    web = cached(f"{name}_web", scrapers.scrape_website, lead["website"])
    out = assess.assess(lead, li, web)
    r = out["result"]
    print(f"\n=== {lead['name']} | {out['niche']} | {out['primary_service']}")
    print(f"summary: {out['company_summary']}")
    print(f"SCORE {r['score']}/100 | priority {r['priority']} | confidence {r['confidence']} | rubric {r['rubric_version']}")
    for b in r["breakdown"]:
        print(f"  {b['label']:<34} {b['level']:<8} {b['points']:>4}/{b['max_points']:<3} [{b['confidence']}] {b['evidence'][:150]} {('(' + b['note'] + ')') if b['note'] else ''}")
    print("  missing:", ", ".join(r["missing"]) or "none")
