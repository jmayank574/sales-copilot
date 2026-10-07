import json
import logging
import os

import gspread
from dotenv import load_dotenv
from gspread.utils import rowcol_to_a1

load_dotenv()
log = logging.getLogger("copilot.sheets")

TAB_NAME = os.environ.get("GOOGLE_SHEET_TAB", "Copilot")

HEADERS = [
    "Full Name",
    "Email",
    "Phone Number",
    "Company Website",
    "LinkedIn",
    "Niche/Industry",
    "Primary Service",
    "Company Summary",
    "Fit Score (0-100)",
    "Priority",
    "Confidence",
    "Route",
    "Next Action",
    "Score Evidence",
    "Missing Info",
    "Personalized Icebreaker",
    "Discovery Questions",
    "Likely Insurance Needs (to confirm)",
    "Likely Objections & Replies",
    "Follow-up Email Draft",
    "Status",
    "Received At",
    # Human-review columns, filled in by the rep
    "Approved by Rep?",
    "Edited Icebreaker",
    "Actual Lead Quality",
    "Meeting Booked?",
    "Qualified?",
    "Quote Created?",
    "Won or Lost?",
    "Reason Lost",
]
EMAIL_COL = HEADERS.index("Email") + 1
WRAP_COLS = [
    "Company Summary", "Next Action", "Score Evidence", "Missing Info", "Personalized Icebreaker",
    "Discovery Questions", "Likely Insurance Needs (to confirm)", "Likely Objections & Replies",
    "Follow-up Email Draft",
]


def _client() -> gspread.Client:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        return gspread.service_account_from_dict(json.loads(raw))
    return gspread.service_account(filename=os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"])


def _format_new_tab(ws: gspread.Worksheet) -> None:
    """Best-effort formatting; never fails the pipeline."""
    try:
        last = rowcol_to_a1(1, len(HEADERS))
        ws.format(f"A1:{last}", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.89, "green": 0.93, "blue": 0.99}})
        ws.freeze(rows=1)
        ws.format(f"A2:{rowcol_to_a1(1000, len(HEADERS))}", {"verticalAlignment": "TOP"})
        for name in WRAP_COLS:
            c = HEADERS.index(name) + 1
            ws.format(f"{rowcol_to_a1(2, c)}:{rowcol_to_a1(1000, c)}", {"wrapStrategy": "WRAP"})
            ws.set_column_width(c, 320)
    except Exception:
        log.warning("Could not format the new tab", exc_info=True)


def _worksheet() -> gspread.Worksheet:
    book = _client().open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        return book.worksheet(TAB_NAME)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title=TAB_NAME, rows=1000, cols=len(HEADERS))
        ws.update(range_name=f"A1:{rowcol_to_a1(1, len(HEADERS))}", values=[HEADERS])
        _format_new_tab(ws)
        return ws


def ensure_headers(ws: gspread.Worksheet) -> None:
    if ws.row_values(1) != HEADERS:
        ws.update(range_name=f"A1:{rowcol_to_a1(1, len(HEADERS))}", values=[HEADERS])


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
