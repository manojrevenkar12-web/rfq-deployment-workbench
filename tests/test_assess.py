from __future__ import annotations

from rdw.assess import compare, configure, judge, recommend
from rdw.config import Capability, customer
from rdw.models import Requirement, Source


def req(kind: str, value: object, priority: str = "mandatory", rid: str = "T-01") -> Requirement:
    return Requirement(
        id=rid,
        source=Source(doc="spec", file="spec.pdf", locator="p1", text="x"),
        kind=kind,
        label=kind,
        value=value,
        priority=priority,
    )  # type: ignore[arg-type]


def test_limits_give_comply_clarify_deviate() -> None:
    cap = Capability("max", 24, 36, "major")
    assert [compare(cap, v)[0] for v in (24, 30, 48)] == ["comply", "clarify", "deviate"]
    lead = Capability("min", 52, 44, "major")
    assert [compare(lead, v)[0] for v in (60, 46, 30)] == ["comply", "clarify", "deviate"]
    temp = Capability("range", [-25, 45], [-30, 45], "major")
    assert [compare(temp, v)[0] for v in ([-20, 40], [-30, 45], [-40, 40])] == ["comply", "clarify", "deviate"]


def test_red_flags_and_their_severity() -> None:
    c = customer("gleiswerk")
    knock = judge(req("track_gauge_mm", 1520), c)
    assert (knock.verdict, knock.red_flag, knock.severity) == ("deviate", True, "knockout")
    soft = judge(req("track_gauge_mm", 1520, "desirable"), c)
    assert soft.severity == "minor"
    commercial = judge(req("warranty_months", 36), c)
    assert (commercial.verdict, commercial.red_flag, commercial.severity) == ("clarify", True, "major")
    technical = judge(req("availability_percent", 97), c)
    assert (technical.verdict, technical.red_flag) == ("clarify", False)
    assert judge(req("penalty_cap_percent", "unlimited"), c).verdict == "deviate"


def test_norms_against_the_company_profile() -> None:
    c = customer("voltaro")
    assert judge(req("norm", "ISO 15118-20"), c).verdict == "deviate"
    assert judge(req("norm", "IEC 61851-23"), c).verdict == "comply"
    assert judge(req("norm", "UL 2202"), c).verdict == "clarify"


def test_variant_and_bid_decision() -> None:
    c = customer("voltaro")
    reqs = [judge(req("charging_power_kw", 300, rid="a"), c), judge(req("warranty_months", 48, rid="b"), c)]
    config = configure(reqs, "Schnellladesäulen", c)
    assert config.variant == "VOLT 400"
    assert recommend(reqs, config).decision == "bid_with_conditions"
    too_much = [judge(req("charging_power_kw", 480), c)]
    rec = recommend(too_much, configure(too_much, "", c))
    assert rec.decision == "no_bid" and rec.knockouts == ["T-01"]
    rail = customer("gleiswerk")
    assert configure([], "Beschaffung einer Gleisstopfmaschine", rail).variant == "GW Stopf 08"
