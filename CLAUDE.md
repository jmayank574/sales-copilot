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

## Modules
- `app/typeform.py`: verify signature, map answers to the 5 lead fields
- `app/scrapers.py`: Apify calls for LinkedIn and website
- `app/enrich.py`: Claude prompt, JSON schema, validation
- `app/sheets.py`: dedupe on email, append row
- `app/main.py`: `/webhook`, returns 200 fast, processes in a background task

## Sheet columns (in order)
Full Name | Email | Phone | Company Website | LinkedIn URL | Niche/Industry | Primary Service | ICP Fit Score | ICP Fit Reason | Personalized Icebreaker | Status | Received At

Status values: `ok`, `partial` (one scraper failed), `error` (includes the error text).

## ICP scoring rubric (DRAFT, derived from fernstone.com)
Score is an integer 1-10 for likelihood of being a real, insurable business buyer. 9-10 means an established operating business with a decision-maker as contact. 1-2 means not a business buyer or not enough information. Full wording is in `app/enrich.py`.

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
