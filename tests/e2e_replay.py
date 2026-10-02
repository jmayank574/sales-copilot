"""Replay a fake Typeform payload through /webhook, print the sheet row, then delete it.
Run: python -m tests.e2e_replay [--keep]"""
import sys

from fastapi.testclient import TestClient

from app import sheets
from app.main import app

EMAIL = "bill.gates.demo@example.com"


def field(fid, title, ftype):
    return {"id": fid, "title": title, "type": ftype, "ref": fid}


PAYLOAD = {
    "form_response": {
        "definition": {
            "fields": [
                field("f1", "What's your full name?", "short_text"),
                field("f2", "What's your email?", "email"),
                field("f3", "Phone number", "phone_number"),
                field("f4", "Company website", "website"),
                field("f5", "Your LinkedIn profile URL", "website"),
            ]
        },
        "answers": [
            {"type": "text", "text": "Bill Gates", "field": {"id": "f1", "ref": "f1", "type": "short_text"}},
            {"type": "email", "email": EMAIL, "field": {"id": "f2", "ref": "f2", "type": "email"}},
            {"type": "phone_number", "phone_number": "(demo - not real)", "field": {"id": "f3", "ref": "f3", "type": "phone_number"}},
            {"type": "url", "url": "https://www.gatesnotes.com/", "field": {"id": "f4", "ref": "f4", "type": "website"}},
            {"type": "url", "url": "https://www.linkedin.com/in/williamhgates/", "field": {"id": "f5", "ref": "f5", "type": "website"}},
        ],
    }
}

r = TestClient(app).post("/webhook", json=PAYLOAD)
print("webhook:", r.status_code, r.json())

ws = sheets._worksheet()
cell = ws.find(EMAIL, in_column=sheets.EMAIL_COL)
row = dict(zip(sheets.HEADERS, ws.row_values(cell.row)))
for k, v in row.items():
    print(f"{k}: {v}")
if "--keep" not in sys.argv:
    ws.delete_rows(cell.row)
    print("(test row deleted)")
