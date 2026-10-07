"""Run the assessment N times on cached data and show score spread. Run: python -m tests.variance_check roehl 4"""
import json, sys
from collections import Counter
from app import assess
from tests.dryrun_assess import LEADS, CACHE

key, n = sys.argv[1], int(sys.argv[2])
lead = LEADS[key]
load = lambda k: json.loads((CACHE / f"{key}_{k}.json").read_text(encoding="utf-8")) if (CACHE / f"{key}_{k}.json").exists() else None
li, web = load("li"), load("web")
scores, sizes = [], Counter()
for _ in range(n):
    r = assess.assess(lead, li, web)["result"]
    scores.append(r["score"])
    sizes[next(b["level"] for b in r["breakdown"] if b["key"] == "company_size")] += 1
print(key, "scores:", scores, "| company_size levels:", dict(sizes))
