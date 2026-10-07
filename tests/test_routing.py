from app import routing


def res(priority, confidence):
    return {"priority": priority, "confidence": confidence}


def test_no_data_needs_info():
    assert routing.decide(None, no_data=True)["route"] == "Needs info"


def test_low_confidence_beats_priority():
    assert routing.decide(res("High", "Low"), no_data=False)["route"] == "Needs info"
    assert routing.decide(res("Low", "Low"), no_data=False)["route"] == "Needs info"


def test_priorities_with_adequate_confidence():
    assert routing.decide(res("High", "Medium"), no_data=False)["route"] == "Call now"
    assert routing.decide(res("Medium", "High"), no_data=False)["route"] == "Follow up"
    d = routing.decide(res("Low", "Medium"), no_data=False)
    assert d["route"] == "Nurture / disqualify" and d["rule"] == "low"
