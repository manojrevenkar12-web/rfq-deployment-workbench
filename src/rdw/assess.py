"""Red flags, norms, bid / no-bid and configuration: the requirements held against what the customer can meet."""

from __future__ import annotations

from typing import Any

from .config import Capability, Customer, settings
from .models import BidRecommendation, Configuration, NormFinding, Requirement, Verdict

SEVERITY_ORDER = {"minor": 0, "major": 1, "knockout": 2}


def compare(cap: Capability, value: Any) -> tuple[Verdict, str]:
    """(verdict, reason) for a requested value against a capability."""
    op, std, lim = cap.op, cap.standard, cap.limit
    if value == "unlimited":
        return "deviate", "unlimited, the company accepts a cap"
    if op == "max":
        if value <= std:
            return "comply", f"{value} is within the standard of {std}"
        if value <= lim:
            return "clarify", f"{value} is above the standard {std} but within {lim}: needs approval or a surcharge"
        return "deviate", f"{value} is beyond what the company offers ({lim})"
    if op == "min":
        if value >= std:
            return "comply", f"{value} meets the standard of {std}"
        if value >= lim:
            return "clarify", f"{value} is below the standard {std} but not below {lim}: needs approval"
        return "deviate", f"{value} is below what the company can do ({lim})"
    if op == "range":
        lo, hi = value
        if std[0] <= lo and hi <= std[1]:
            return "comply", f"{lo}..{hi} inside {std[0]}..{std[1]}"
        if lim[0] <= lo and hi <= lim[1]:
            return "clarify", f"{lo}..{hi} needs the option range {lim[0]}..{lim[1]}"
        return "deviate", f"{lo}..{hi} outside {lim[0]}..{lim[1]}"
    if op == "set":
        norm = {str(x).lower() for x in std}
        if str(value).lower() in norm:
            return "comply", f"{value} is offered"
        if str(value).lower() in {str(x).lower() for x in lim}:
            return "clarify", f"{value} only on request"
        return "deviate", f"{value} is not offered"
    if op == "bool":
        if std:
            return "comply", "offered"
        return ("clarify", "on the roadmap") if lim else ("deviate", "not offered")
    raise ValueError(op)


def judge(req: Requirement, customer: Customer) -> Requirement:
    s = settings()["red_flags"]
    if req.kind == "procedural":
        req.verdict, req.reason = "comply", "about the bid, not the product: goes on the submission checklist"
    elif req.kind == "other":
        req.verdict, req.reason = "clarify", "not in the vocabulary: a person decides"
    elif req.kind == "norm":
        status = norm_status(str(req.value), customer)
        verdicts: dict[str, Verdict] = {"certified": "comply", "not_certified": "deviate", "unknown": "clarify"}
        req.verdict = verdicts[status]
        req.reason = {
            "certified": "certified",
            "not_certified": "not certified",
            "unknown": "not known to the company profile: ask quality",
        }[status]
    else:
        cap = customer.capabilities.get(req.kind)
        if cap is None:
            req.verdict, req.reason = "clarify", "no capability recorded for this kind"
        elif req.value is None:
            req.verdict, req.reason = "clarify", "no value found in the text"
        else:
            try:
                req.verdict, req.reason = compare(cap, req.value)
            except (TypeError, ValueError):
                req.verdict, req.reason = "clarify", "value could not be compared"
    spec = customer.kinds.get(req.kind)
    cap = customer.capabilities.get(req.kind)
    commercial = bool(spec and spec.commercial)
    base = cap.severity if cap else "major"
    flag = req.verdict == "deviate" or (
        req.verdict == "clarify"
        and commercial
        and SEVERITY_ORDER[base] >= SEVERITY_ORDER[s["commercial_clarify_severity"]]
    )
    req.red_flag = flag
    if not flag:
        req.severity = None
    elif req.priority == "desirable":
        req.severity = "minor"
    elif req.verdict == "deviate":
        req.severity = base if req.kind != "norm" else "major"  # type: ignore[assignment]
    else:
        req.severity = "major" if base in ("knockout", "major") else "minor"
    return req


def norm_status(norm: str, customer: Customer) -> str:
    key = norm.replace(" ", "").lower()
    if any(n.replace(" ", "").lower() == key for n in customer.norms_certified):
        return "certified"
    if any(n.replace(" ", "").lower() == key for n in customer.norms_not_certified):
        return "not_certified"
    return "unknown"


def norms_report(reqs: list[Requirement], customer: Customer) -> list[NormFinding]:
    cited: dict[str, list[str]] = {}
    for r in reqs:
        for n in r.norms:
            cited.setdefault(n, []).append(r.id)
    return [
        NormFinding(norm=n, status=norm_status(n, customer), cited_in=ids)  # type: ignore[arg-type]
        for n, ids in sorted(cited.items())
    ]


def configure(reqs: list[Requirement], subject: str, customer: Customer) -> Configuration:
    cat = customer.catalog
    by = cat["select_by"]
    variants = cat["variants"]
    if by == "subject":
        low = subject.lower()
        for v in variants:
            if any(m in low for m in v["match"]):
                return Configuration(variant=v["name"], reason=f"the tender asks for a {subject.split()[-1]}")
        return Configuration(variant=None, reason="no product line matches the tender subject")
    values = [r.value for r in reqs if r.kind == by and r.value is not None]
    if not values:
        return Configuration(variant=None, reason=f"the tender states no {by.replace('_', ' ')}")
    if all(isinstance(v, (int, float)) for v in values):
        need = max(values)
        fits = sorted((v for v in variants if v[by] >= need), key=lambda v: v[by])
        if fits:
            return Configuration(
                variant=fits[0]["name"], reason=f"smallest variant covering {need} ({by.replace('_', ' ')})"
            )
        return Configuration(variant=None, reason=f"no variant covers {need}")
    for v in variants:
        if str(v[by]).lower() == str(values[0]).lower():
            return Configuration(variant=v["name"], reason=f"{values[0]} is built as {v['name']}")
    return Configuration(variant=None, reason=f"{values[0]} is not in the product range")


def recommend(reqs: list[Requirement], config: Configuration) -> BidRecommendation:
    rules = settings()["bid"]
    knockouts = [r for r in reqs if r.red_flag and r.severity == "knockout" and r.priority == "mandatory"]
    majors = [r for r in reqs if r.red_flag and r.severity == "major"]
    reasons = []
    if knockouts and "knockout_deviation" in rules["no_bid_on"]:
        reasons += [f"cannot meet: {r.label} ({r.value})" for r in knockouts]
    if config.variant is None and "no_variant" in rules["no_bid_on"]:
        reasons.append(f"no product fits: {config.reason}")
    if reasons:
        return BidRecommendation(decision="no_bid", reasons=reasons, knockouts=[r.id for r in knockouts], conditions=[])
    if len(majors) >= rules["conditions_on_major_flags"]:
        return BidRecommendation(
            decision="bid_with_conditions",
            reasons=[f"{len(majors)} terms need a decision before the offer"],
            knockouts=[],
            conditions=[f"{r.label}: {r.reason}" for r in majors],
        )
    return BidRecommendation(
        decision="bid", reasons=["every mandatory requirement can be met"], knockouts=[], conditions=[]
    )
