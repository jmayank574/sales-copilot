import json
import os

import gspread
from dotenv import load_dotenv

load_dotenv()

HEADERS = [
    "Full Name",
    "Email",
    "Phone Number",
    "Company Website",
    "LinkedIn",
    "Niche/Industry",
    "Primary Service",
    "ICP Fit Score (1-10)",
    "ICP Fit Reason",
    "Personalized Icebreaker",
    "Status",
    "Received At",
]
EMAIL_COL = 2


def _worksheet() -> gspread.Worksheet:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        client = gspread.service_account_from_dict(json.loads(raw))
    else:
        client = gspread.service_account(filename=os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"])
    return client.open_by_key(os.environ["GOOGLE_SHEET_ID"]).sheet1


def ensure_headers(ws: gspread.Worksheet) -> None:
    """Write the full header row if the extra Status/Received At columns are missing."""
    if ws.row_values(1) != HEADERS:
        ws.update(range_name="A1:L1", values=[HEADERS])


def email_exists(ws: gspread.Worksheet, email: str) -> bool:
    existing = {e.strip().lower() for e in ws.col_values(EMAIL_COL)[1:]}
    return email.strip().lower() in existing


def append_lead(row: dict) -> bool:
    """Append a lead row keyed by HEADERS. Returns False if the email is already present."""
    ws = _worksheet()
    ensure_headers(ws)
    if email_exists(ws, row["Email"]):
        return False
    ws.append_row([row.get(h, "") for h in HEADERS], value_input_option="RAW")
    return True
