import json
from pathlib import Path

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "rubric.json"
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


def load_rubric(path: Path = RUBRIC_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def enabled_factors(rubric: dict) -> list[dict]:
    return [f for f in rubric["factors"] if f.get("enabled")]


def compute(judgments: dict, rubric: dict) -> dict:
    """Turn per-factor judgments into a score. Claude supplies level, evidence and
    confidence; points and priority are computed here, never by the model.

    A level other than 'unknown' without evidence is downgraded to 'unknown'.
    Disabled factors are excluded and the total is rescaled over the enabled ones.
    """
    factors = enabled_factors(rubric)
    max_total = sum(f["max_points"] for f in factors)
    earned = 0.0
    conf_num = 0.0
    breakdown = []

    for f in factors:
        j = judgments.get(f["key"]) or {}
        level = j.get("level", "unknown")
        evidence = (j.get("evidence") or "").strip()
        confidence = (j.get("confidence") or "low").lower()
        note = ""
        if level not in f["levels"]:
            note = f"invalid level '{level}'"
            level = "unknown"
        if level != "unknown" and not evidence:
            note = "no evidence given, treated as unknown"
            level = "unknown"
        if level == "unknown":
            confidence = "low"
        points = f["max_points"] * f["levels"][level]["fraction"]
        earned += points
        conf_num += CONFIDENCE_WEIGHT.get(confidence, 0.3) * f["max_points"]
        breakdown.append(
            {
                "key": f["key"],
                "label": f["label"],
                "level": level,
                "points": round(points, 1),
                "max_points": f["max_points"],
                "confidence": confidence,
                "evidence": evidence,
                "note": note,
            }
        )

    score = round(earned / max_total * 100) if max_total else 0
    conf = conf_num / max_total if max_total else 0
    confidence_label = "High" if conf >= 0.7 else "Medium" if conf >= 0.45 else "Low"
    bands = rubric["priority_bands"]
    priority = "High" if score >= bands["high"] else "Medium" if score >= bands["medium"] else "Low"
    return {
        "score": score,
        "priority": priority,
        "confidence": confidence_label,
        "missing": [b["label"] for b in breakdown if b["level"] == "unknown"],
        "breakdown": breakdown,
        "rubric_version": rubric["version"],
    }
