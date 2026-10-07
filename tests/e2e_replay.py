"""Replay fake Typeform payloads through /webhook (real scrapers, Claude, sheet), print each row.
Run: python -m tests.e2e_replay adam designer roehl [--delete]
Rows are KEPT in the Copilot tab unless --delete is given."""
import sys

from fastapi.testclient import TestClient

from app import sheets
from app.main import app
from tests.e2e_replay_payload import DEMO_LEADS, make_payload

keys = [a for a in sys.argv[1:] if not a.startswith("--")] or ["adam"]
client = TestClient(app)
ws = sheets._worksheet()

for key in keys:
    name, email, phone, website, linkedin = DEMO_LEADS[key]
    r = client.post("/webhook", json=make_payload(name, email, phone, website, linkedin))
    print(f"\n##### {key}: webhook {r.status_code}")
    cell = ws.find(email, in_column=sheets.EMAIL_COL)
    row = dict(zip(sheets.HEADERS, ws.row_values(cell.row)))
    for k in sheets.HEADERS[:22]:
        if k in ("Phone Number", "Email"):
            continue
        print(f"[{k}]\n{row.get(k, '')}\n")
    if "--delete" in sys.argv:
        ws.delete_rows(cell.row)
        print("(row deleted)")
