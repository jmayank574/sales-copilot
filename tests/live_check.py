"""Send signed + unsigned payloads to the deployed webhook. Run: python -m tests.live_check <base_url> <secret> [--keep]"""
import base64, hashlib, hmac, json, sys, time

import requests

from app import sheets
from tests.e2e_replay_payload import PAYLOAD, EMAIL

base, secret = sys.argv[1].rstrip("/"), sys.argv[2]
body = json.dumps(PAYLOAD).encode()
sig = "sha256=" + base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
h = {"Content-Type": "application/json"}

r = requests.post(base + "/webhook", data=body, headers=h, timeout=120)
print("unsigned ->", r.status_code, "(expect 401)")
r = requests.post(base + "/webhook", data=body, headers={**h, "Typeform-Signature": sig}, timeout=120)
print("signed   ->", r.status_code, r.text, "(expect 200)")

ws = sheets._worksheet()
for i in range(18):
    time.sleep(10)
    try:
        cell = ws.find(EMAIL, in_column=sheets.EMAIL_COL)
    except Exception:
        cell = None
    if cell:
        row = dict(zip(sheets.HEADERS, ws.row_values(cell.row)))
        for k, v in row.items():
            print(f"{k}: {v}")
        if "--keep" not in sys.argv:
            ws.delete_rows(cell.row)
            print("(test row deleted)")
        break
else:
    print("no row after 180s - check Render logs")
