"""Guards against a broken edit to the founder-editable knowledge files."""
import json
import re
from pathlib import Path

import pytest

K = Path(__file__).resolve().parent.parent / "knowledge"
MD_FILES = ["fernstone_context.md", "brief_guidelines.md", "objections.md"]
VERTICALS = [
    "Security", "Garage", "Daycares", "Staffing", "Bars and restaurants", "Fire and lifesafety",
    "Pest control", "Med spas", "Fleet repair", "Nightlife", "Hotels",
]


def load(name):
    return json.loads((K / name).read_text(encoding="utf-8"))


def test_rubric_structure():
    r = load("rubric.json")
    keys = [f["key"] for f in r["factors"]]
    assert len(keys) == len(set(keys)), "duplicate factor keys"
    for f in r["factors"]:
        assert f["max_points"] > 0
        assert "unknown" in f["levels"], f"{f['key']} needs an 'unknown' level"
        for name, lv in f["levels"].items():
            assert 0 <= lv["fraction"] <= 1, f"{f['key']}.{name} fraction out of range"
            assert lv["definition"].strip()
    assert sum(f["max_points"] for f in r["factors"] if f["enabled"]) > 0
    assert r["priority_bands"]["high"] > r["priority_bands"]["medium"] > 0


def test_rubric_changelog_matches_version():
    r = load("rubric.json")
    assert r["changelog"][-1]["version"] == r["version"], "add a changelog entry when you bump the version"


def test_routing_covers_every_priority_and_no_data():
    rules = load("routing.json")["rules"]
    names = [x["name"] for x in rules]
    assert len(names) == len(set(names))
    covered = {p for x in rules for p in x["when"].get("priority", [])}
    assert {"High", "Medium", "Low"} <= covered
    assert any(x["when"].get("no_data") for x in rules)
    assert all(x["route"] and x["action"] for x in rules)


@pytest.mark.parametrize("name", MD_FILES)
def test_markdown_has_frontmatter(name):
    text = (K / name).read_text(encoding="utf-8")
    m = re.match(r"---\nname: .+\ndescription: .+\n---\n", text)
    assert m, f"{name} needs name and description frontmatter"
    assert "## When to Use" in text, f"{name} needs a 'When to Use' section"


def test_context_has_published_verticals_and_source_tags():
    text = (K / "fernstone_context.md").read_text(encoding="utf-8")
    for v in VERTICALS:
        assert v in text, f"vertical '{v}' missing from context"
    assert "[site" in text and "[assumption]" in text and "[job post]" in text


def test_rubric_industry_factor_names_verticals():
    r = load("rubric.json")
    guidance = next(f for f in r["factors"] if f["key"] == "target_industry")["guidance"]
    assert "Fire and lifesafety" in guidance
