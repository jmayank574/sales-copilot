from app import scoring

RUBRIC = scoring.load_rubric()


def j(level, evidence="x", confidence="high"):
    return {"level": level, "evidence": evidence, "confidence": confidence}


def all_factors(level):
    return {f["key"]: j(level) for f in scoring.enabled_factors(RUBRIC)}


def test_all_strong_is_100_and_high():
    r = scoring.compute(all_factors("strong"), RUBRIC)
    assert r["score"] == 100 and r["priority"] == "High" and r["confidence"] == "High"


def test_all_unknown_is_zero_low_with_everything_missing():
    r = scoring.compute({}, RUBRIC)
    assert r["score"] == 0 and r["priority"] == "Low" and r["confidence"] == "Low"
    assert len(r["missing"]) == len(scoring.enabled_factors(RUBRIC))


def test_level_without_evidence_is_downgraded():
    judgments = all_factors("strong")
    judgments["operational_risk"] = j("strong", evidence="")
    r = scoring.compute(judgments, RUBRIC)
    row = next(b for b in r["breakdown"] if b["key"] == "operational_risk")
    assert row["level"] == "unknown" and row["points"] == 0 and row["note"]


def test_invalid_level_is_unknown():
    judgments = all_factors("strong")
    judgments["company_size"] = j("excellent")
    r = scoring.compute(judgments, RUBRIC)
    assert next(b for b in r["breakdown"] if b["key"] == "company_size")["level"] == "unknown"


def test_disabled_geography_is_excluded_and_total_rescaled():
    keys = {b["key"] for b in scoring.compute({}, RUBRIC)["breakdown"]}
    assert "geography" not in keys
    assert scoring.compute(all_factors("strong"), RUBRIC)["score"] == 100


def test_partial_is_half_points():
    judgments = {k: j("partial") for k in all_factors("strong")}
    assert scoring.compute(judgments, RUBRIC)["score"] == 50


def test_unknown_trigger_caps_score_below_100_but_can_still_be_high():
    judgments = all_factors("strong")
    judgments["buying_trigger"] = j("unknown")
    r = scoring.compute(judgments, RUBRIC)
    assert 80 <= r["score"] < 100 and r["priority"] == "High"


def test_decision_maker_capped_without_linkedin():
    r = scoring.compute(all_factors("strong"), RUBRIC, {"linkedin_available": False})
    dm = next(b for b in r["breakdown"] if b["key"] == "decision_maker")
    assert dm["level"] == "partial" and dm["points"] == 7.5 and dm["confidence"] == "low" and dm["note"]
    assert r["score"] < 100


def test_outbound_owner_named_on_site_is_not_capped():
    ctx = {"linkedin_available": False, "contact_source": "company_website"}
    r = scoring.compute(all_factors("strong"), RUBRIC, ctx)
    assert next(b for b in r["breakdown"] if b["key"] == "decision_maker")["level"] == "strong"
    assert r["score"] == 100


def test_decision_maker_not_capped_with_linkedin():
    r = scoring.compute(all_factors("strong"), RUBRIC, {"linkedin_available": True})
    assert r["score"] == 100
