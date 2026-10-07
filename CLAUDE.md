# Sales Co-Pilot

Lead enrichment agent. A Typeform submission triggers a webhook. The script scrapes the lead's LinkedIn and company website, asks Claude to enrich and score the lead, then appends a row to a Google Sheet for the sales rep.

## Business context
- Company (demo): Fernstone Insurance (fernstone.com), a commercial insurance brokerage for businesses, with a platform for COIs, claims, policies and renewals.
- Good fit per their site: businesses that want to save money without losing coverage, know their business well, are well-managed, and want a straightforward broker relationship.
- Not a fit: people wanting the fastest quote regardless of price, or unwilling to share business details.
- Rep use: the row is read before a call. The icebreaker opens a personalized conversation.
- The scoring prompt is `SYSTEM_PROMPT` in `app/enrich.py`. Swap it (and this section) to retarget for another company.

## Stack
- Python, FastAPI webhook (`app/main.py`), run with `uvicorn app.main:app`
- Apify actors: `harvestapi/linkedin-profile-scraper` (profile only; posts actor skipped to save cost), `apify/website-content-crawler` (company site)
- Claude via the Anthropic API for enrichment (structured JSON output)
- Google Sheets via gspread with a service account

## Pipeline (local; not yet deployed)
Scrape (LinkedIn + website) -> `app/assess.py` (Claude returns level/evidence/confidence per factor) -> `app/scoring.py` (code computes score + priority) -> `app/routing.py` (rules in `knowledge/routing.json`) -> `app/brief.py` (rep brief, skipped for Low) -> `app/sheets.py` (tab `Copilot`).
Knowledge files in `knowledge/` (rubric.json, fernstone_context.md, brief_guidelines.md, objections.md, routing.json) hold all business content. Facts are tagged [site] or [assumption].

## Modules
- `app/typeform.py`: verify signature, map answers to the 5 lead fields
- `app/scrapers.py`: Apify calls for LinkedIn and website
- `app/enrich.py`: Claude prompt, JSON schema, validation
- `app/sheets.py`: dedupe on email, append row
- `app/main.py`: `/webhook`, returns 200 fast, processes in a background task
- `app/enrich.py`: legacy single-call scorer, no longer used by the pipeline

## Sheet
Tab `Copilot`, columns defined by `HEADERS` in `app/sheets.py` (lead fields, score, priority, confidence, route, evidence, brief, status, then rep-review columns). The old `Sheet1` tab is the legacy format.

Status values: `ok`, `partial: ...` (a scraper or the brief failed), `error: ...`.

## Scoring
Six weighted factors in `knowledge/rubric.json` (industry 25, size 15, geography 10 [disabled until supported states are known], decision-maker 15, operational risk 20, buying trigger 15). Claude never produces the total; code does. Unknown or evidence-free factors score 0. Priority bands: High 70+, Medium 40+, Low below. Draft weights and bands for the founder to confirm.

## Icebreaker rules
- 1-2 short sentences, under 40 words, young peer-to-peer tone, anchored on one concrete detail, ends with a light question.
- Banned: generic openers ("I came across your profile"), flattery clichés, any pitch or product mention.

## Conventions
- Secrets live in `.env` only (git-ignored). Never hardcode or log them.
- Missing scrape data is not a crash. Write the row with `partial` or `error` status.
- Dedupe on email before appending.

## Commands
- Install: `pip install -r requirements.txt`
- Deploy: Render via `render.yaml` (env vars incl. `GOOGLE_SERVICE_ACCOUNT_JSON` = full JSON key contents)
- Run locally: `uvicorn app.main:app --reload --port 8000`
- Tests: `pytest`
