import base64
import hashlib
import hmac


def verify_signature(raw_body: bytes, header: str | None, secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    digest = base64.b64encode(hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(f"sha256={digest}", header)


def _answer_value(a: dict) -> str:
    t = a.get("type")
    if t == "choice":
        return (a.get("choice") or {}).get("label", "")
    return str(a.get(t, "") or "").strip()


def parse_lead(payload: dict) -> dict:
    """Map a Typeform webhook payload to name/email/phone/website/linkedin.

    Fields are matched by answer type first, then by keywords in the question title,
    so it works without knowing the field refs in advance.
    """
    fr = payload["form_response"]
    titles = {f["id"]: (f.get("title") or "").lower() for f in fr.get("definition", {}).get("fields", [])}
    lead = {"name": "", "email": "", "phone": "", "website": "", "linkedin": ""}

    for a in fr.get("answers", []):
        value = _answer_value(a)
        title = titles.get(a["field"]["id"], "") + " " + (a["field"].get("ref") or "").lower()
        if a["type"] == "email":
            lead["email"] = value
        elif a["type"] == "phone_number":
            lead["phone"] = value
        elif "linkedin" in title:
            lead["linkedin"] = value
        elif "website" in title or "company" in title or "url" in title or "site" in title:
            lead["website"] = value
        elif "name" in title:
            lead["name"] = value
        elif a["type"] == "url" and not lead["website"]:
            lead["website"] = value
    return lead
