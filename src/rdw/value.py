"""The value case for the SteerCo: hours, money, capacity and days to bid, with every assumption visible and
editable. Built on the replay of the customer's own year (discovery.what_if), not on industry averages."""

from __future__ import annotations

from typing import Any

from .config import settings


def defaults() -> dict[str, Any]:
    v = settings()["value"]
    return {
        "hourly_cost": dict(v["hourly_cost"]),
        "hours_per_person_year": v["hours_per_person_year"],
        "annual_fee": v["annual_fee"],
        "volume_growth": 0.0,
    }


def value_case(what_if: dict[str, Any], assumptions: dict[str, Any] | None = None) -> dict[str, Any]:
    a = defaults()
    for k, v in (assumptions or {}).items():
        if k == "hourly_cost" and isinstance(v, dict):
            a["hourly_cost"].update({r: float(x) for r, x in v.items()})
        elif k in a:
            a[k] = float(v)
    scale = 365 / max(1, what_if["period_days"]) * (1 + a["volume_growth"])
    by_role = []
    for role, hours in sorted(what_if["hours_saved_by_role"].items(), key=lambda kv: -kv[1]):
        if hours <= 0:
            continue
        yearly = hours * scale
        rate = a["hourly_cost"].get(role, 0)
        by_role.append(
            {
                "role": role,
                "hours": round(yearly),
                "rate": rate,
                "value": round(yearly * rate),
                "people": round(yearly / a["hours_per_person_year"], 2),
            }
        )
    gross = sum(r["value"] for r in by_role)
    net = gross - a["annual_fee"]
    lt = what_if["lead_time_days"]
    return {
        "assumptions": a,
        "by_role": by_role,
        "hours_per_year": sum(r["hours"] for r in by_role),
        "capacity_people": round(sum(r["people"] for r in by_role), 2),
        "gross_per_year": gross,
        "net_per_year": net,
        "payback_months": round(12 * a["annual_fee"] / gross, 1) if gross > 0 else None,
        "lead_time_days": lt,
        "statement": _statement(by_role, gross, net, lt, a),
    }


def _statement(by_role: list[dict[str, Any]], gross: float, net: float, lt: dict[str, Any], a: dict[str, Any]) -> str:
    if not by_role:
        return "With the agents in scope at their current readiness, nothing changes yet: raise readiness first."
    top = by_role[0]
    people = sum(r["people"] for r in by_role)
    return (
        f"About {sum(r['hours'] for r in by_role):,} hours a year come back, {top['hours']:,} of them in "
        f"{top['role'].replace('_', ' ')}: the work of {people:.1f} people, worth {gross:,.0f} {settings()['value']['currency']} "
        f"against a fee of {a['annual_fee']:,.0f}. Half of all bids go out within {lt['after']} days instead of "
        f"{lt['before']} (between {lt['saved_low']} and {lt['saved_high']} days faster, 90 % of resamples)."
    )
