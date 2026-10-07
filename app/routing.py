import json
from pathlib import Path

ROUTING_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "routing.json"


def load_routing(path: Path = ROUTING_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decide(result: dict | None, no_data: bool, routing: dict | None = None) -> dict:
    """Pick the first matching rule. result is the output of scoring.compute (or None on failure)."""
    routing = routing or load_routing()
    facts = {
        "no_data": no_data or result is None,
        "priority": result["priority"] if result else None,
        "confidence": result["confidence"] if result else "Low",
    }
    for rule in routing["rules"]:
        when = rule["when"]
        if "no_data" in when and facts["no_data"] != when["no_data"]:
            continue
        if "confidence" in when and facts["confidence"] not in when["confidence"]:
            continue
        if "priority" in when and facts["priority"] not in when["priority"]:
            continue
        return {"rule": rule["name"], "route": rule["route"], "action": rule["action"]}
    return {"rule": "default", "route": "Needs info", "action": "No routing rule matched. Rep to review."}
