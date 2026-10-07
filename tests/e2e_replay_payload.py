"""Builds fake Typeform webhook payloads for tests."""


def field(fid, title, ftype):
    return {"id": fid, "title": title, "type": ftype, "ref": fid}


def make_payload(name, email, phone, website, linkedin):
    return {
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
                {"type": "text", "text": name, "field": {"id": "f1", "ref": "f1", "type": "short_text"}},
                {"type": "email", "email": email, "field": {"id": "f2", "ref": "f2", "type": "email"}},
                {"type": "phone_number", "phone_number": phone, "field": {"id": "f3", "ref": "f3", "type": "phone_number"}},
                {"type": "url", "url": website, "field": {"id": "f4", "ref": "f4", "type": "website"}},
                {"type": "url", "url": linkedin, "field": {"id": "f5", "ref": "f5", "type": "website"}},
            ],
        }
    }


# Used by tests/live_check.py
EMAIL = "bill.gates.demo@example.com"
PAYLOAD = make_payload(
    "Bill Gates", EMAIL, "(demo - not real)",
    "https://www.gatesnotes.com/", "https://www.linkedin.com/in/williamhgates/",
)

DEMO_LEADS = {
    "adam": ("Adam Levine", "adam.demo@example.com", "(demo - not real)",
             "https://www.capitolfire.com/", "https://www.linkedin.com/in/adam-levine-cfs/"),
    "designer": ("Jesse Nyberg", "designer.demo@example.com", "(demo - not real)",
                 "https://jessenyberg.design/", "https://www.linkedin.com/in/jessenyberg/"),
    "roehl": ("Rick Roehl", "roehl.demo@example.com", "(demo - not real)",
              "https://www.roehl.jobs/", ""),
    "gates": ("Bill Gates", EMAIL, "(demo - not real)",
              "https://www.gatesnotes.com/", "https://www.linkedin.com/in/williamhgates/"),
}
