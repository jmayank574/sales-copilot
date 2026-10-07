"""Send a signed Frey demo payload to the live service, print icebreaker + email, delete the row.
Run: python -m tests.live_brief_check <base_url> <secret>"""
import base64, hashlib, hmac, json, sys, time

import requests

from app import sheets
from tests.e2e_replay_payload import make_payload

base, secret = sys.argv[1].rstrip("/"), sys.argv[2]
email = "frey.livecheck@example.com"
body = json.dumps(make_payload("Mark Frey", email, "(demo - not real)", "https://freyelectric.com",
                               "https://linkedin.com/in/mafrey")).encode()
sig = "sha256=" + base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
r = requests.post(base + "/webhook", data=body, headers={"Content-Type": "application/json", "Typeform-Signature": sig}, timeout=120)
print("signed ->", r.status_code)
ws = sheets._worksheet()
for _ in range(24):
    time.sleep(10)
    try:
        cell = ws.find(email, in_column=sheets.EMAIL_COL)
    except Exception:
        cell = None
    if cell:
        row = dict(zip(sheets.HEADERS, ws.row_values(cell.row)))
        for k in ["Fit Score (0-100)", "Priority", "Route", "Personalized Icebreaker", "Follow-up Email Draft", "Status"]:
            print(f"[{k}]\n{row[k]}\n")
        ws.delete_rows(cell.row)
        print("(test row deleted)")
        break
else:
    print("no row after 240s - check Render logs")
