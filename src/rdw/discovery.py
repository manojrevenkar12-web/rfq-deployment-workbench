"""Discovery: the customer's quote process as their CRM export shows it, before anyone argues about it.

From one row per activity (case, activity, resource, role, start, complete, work hours) it finds where a tender
spends its time: working, queueing for a busy person, or waiting for the buyer. Then it replays the same year
with the agents' effect on each activity to show what changes, and what does not (an agent cannot make a
buyer answer faster).
"""

from __future__ import annotations

import csv
import datetime as dt
import heapq
import random
import statistics as st
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import agents, data_dir, settings

END = ("Submitted", "No bid")
EXTERNAL_ROLES = ("buyer",)
CALENDAR_PER_WORK_HOUR = 168 / 40  # the log's work hours are spread over a working week


@dataclass
class Event:
    case: str
    activity: str
    resource: str
    role: str
    start: dt.datetime
    complete: dt.datetime
    work_hours: float


def load_log(path: Path) -> dict[str, list[Event]]:
    cases: dict[str, list[Event]] = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cases[r["case_id"]].append(
                Event(
                    r["case_id"],
                    r["activity"],
                    r["resource"],
                    r["role"],
                    dt.datetime.fromisoformat(r["start"]),
                    dt.datetime.fromisoformat(r["complete"]),
                    float(r.get("work_hours") or 0),
                )
            )
    for evs in cases.values():
        evs.sort(key=lambda e: (e.start, e.complete))
    return dict(cases)


def _hours(a: dt.datetime, b: dt.datetime) -> float:
    return (b - a).total_seconds() / 3600


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    i = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
    return s[i]


def analyse_log(cases: dict[str, list[Event]]) -> dict[str, Any]:
    submitted = [evs for evs in cases.values() if evs[-1].activity == "Submitted"]
    lead_days = [_hours(evs[0].start, evs[-1].complete) / 24 for evs in submitted]
    acts: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "work": [], "wait": [], "role": ""})
    edges: Counter[tuple[str, str]] = Counter()
    variants: Counter[tuple[str, ...]] = Counter()
    rework = 0
    for evs in cases.values():
        seen: Counter[str] = Counter()
        prev = None
        for e in evs:
            a = acts[e.activity]
            a["count"] += 1
            a["role"] = e.role
            a["work"].append(e.work_hours)
            if prev is not None:
                a["wait"].append(max(0.0, _hours(prev.complete, e.start)))
                edges[(prev.activity, e.activity)] += 1
            seen[e.activity] += 1
            prev = e
        rework += any(n > 1 for a, n in seen.items() if a not in ("Buyer answer", "Clarify with buyer"))
        variants[tuple(e.activity for e in evs)] += 1

    span_days = max(
        1.0,
        _hours(
            min(e.start for evs in cases.values() for e in evs), max(e.complete for evs in cases.values() for e in evs)
        )
        / 24,
    )
    people: dict[str, set[str]] = defaultdict(set)
    work_by_role: dict[str, float] = defaultdict(float)
    for evs in cases.values():
        for e in evs:
            if e.role not in EXTERNAL_ROLES and e.work_hours > 0:
                people[e.role].add(e.resource)
                work_by_role[e.role] += e.work_hours
    capacity = {r: len(p) * span_days / 7 * 40 for r, p in people.items()}
    activities = []
    n_cases = len(cases)
    for name, a in acts.items():
        waits = a["wait"]
        activities.append(
            {
                "activity": name,
                "role": a["role"],
                "count": a["count"],
                "share_of_cases": round(a["count"] / n_cases, 3),
                "work_hours_mean": round(st.fmean(a["work"]), 2) if a["work"] else 0.0,
                "wait_hours_mean": round(st.fmean(waits), 1) if waits else 0.0,
                "wait_hours_per_case": round(sum(waits) / n_cases, 1),
                "waiting_kind": "external" if a["role"] in EXTERNAL_ROLES else "queue",
            }
        )
    activities.sort(key=lambda x: -x["wait_hours_per_case"])
    worst = activities[0] if activities else None
    internal = next((a for a in activities if a["waiting_kind"] == "queue"), None)
    return {
        "cases": n_cases,
        "submitted": len(submitted),
        "no_bid": sum(1 for evs in cases.values() if evs[-1].activity == "No bid"),
        "period_days": round(span_days),
        "lead_time_days": {
            "median": round(st.median(lead_days), 1) if lead_days else 0,
            "p80": round(_pct(lead_days, 0.8), 1),
        },
        "rework_share": round(rework / n_cases, 3) if n_cases else 0,
        "activities": activities,
        "bottleneck": {
            "activity": worst["activity"],
            "kind": worst["waiting_kind"],
            "wait_hours_per_case": worst["wait_hours_per_case"],
        }
        if worst
        else None,
        "internal_bottleneck": {
            "activity": internal["activity"],
            "role": internal["role"],
            "wait_hours_per_case": internal["wait_hours_per_case"],
        }
        if internal
        else None,
        "utilisation": {r: round(work_by_role[r] / capacity[r], 2) for r in sorted(capacity) if capacity[r] > 0},
        "people": {r: len(p) for r, p in sorted(people.items())},
        "edges": [{"from": a, "to": b, "count": n} for (a, b), n in edges.most_common()],
        "variants": [{"path": list(v), "count": n} for v, n in variants.most_common(5)],
        "work_hours_by_role": {r: round(h) for r, h in sorted(work_by_role.items())},
    }


# --------------------------------------------------------------------------- what-if


def effort_factors(readiness: dict[str, dict[str, Any]], scope: list[str] | None = None) -> dict[str, float]:
    """Multiplier per activity from the scoped agents' readiness: 1 - reduction, reductions compound."""
    factors: dict[str, float] = defaultdict(lambda: 1.0)
    for name, agent in agents().items():
        if scope is not None and name not in scope:
            continue
        level = readiness.get(name, {}).get("level", "not_yet")
        if level not in ("automate", "assist"):
            continue
        for activity, cut in agent["activities"].items():
            factors[activity] *= 1 - cut[level]
    return dict(factors)


def replay(cases: dict[str, list[Event]], factors: dict[str, float]) -> dict[str, Any]:
    """Re-runs the same tenders (same arrivals, same people, same buyer delays) with the work per activity scaled."""
    people: dict[str, set[str]] = defaultdict(set)
    for evs in cases.values():
        for e in evs:
            if e.role not in EXTERNAL_ROLES and e.work_hours > 0:
                people[e.role].add(e.resource)
    free = {r: [0.0] * len(p) for r, p in people.items()}
    t0 = min(evs[0].start for evs in cases.values())
    plans = []
    for cid, evs in cases.items():
        steps = []
        prev = None
        for e in evs:
            external = max(0.0, _hours(prev.complete, e.start)) if e.role in EXTERNAL_ROLES and prev else 0.0
            steps.append((e.activity, e.role, e.work_hours * factors.get(e.activity, 1.0), external))
            prev = e
        plans.append((cid, _hours(t0, evs[0].start), steps))
    queue = [(arrive, i, i, 0) for i, (_, arrive, _) in enumerate(plans)]
    heapq.heapify(queue)
    seq = len(plans)
    start_of: dict[int, float] = {}
    lead: dict[str, float] = {}
    hours_by_role: dict[str, float] = defaultdict(float)
    per_activity: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])  # calendar hours: work, wait
    while queue:
        ready, _, i, k = heapq.heappop(queue)
        cid, arrive, steps = plans[i]
        activity, role, work, external = steps[k]
        start_of.setdefault(i, arrive)
        if role in EXTERNAL_ROLES or work == 0:
            end = ready + external
            per_activity[activity][1] += external
        else:
            slots = free.get(role) or [0.0]
            j = min(range(len(slots)), key=lambda x: slots[x])
            begin = max(ready, slots[j])
            end = begin + work * CALENDAR_PER_WORK_HOUR
            slots[j] = end
            hours_by_role[role] += work
            per_activity[activity][0] += end - begin
            per_activity[activity][1] += begin - ready
        if k + 1 < len(steps):
            seq += 1
            heapq.heappush(queue, (end, seq, i, k + 1))
        elif activity == "Submitted":
            lead[cid] = (end - start_of[i]) / 24
    return {"lead_days": lead, "hours_by_role": dict(hours_by_role), "per_activity": dict(per_activity)}


def _timeline(cases: dict[str, list[Event]], base: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Where the average tender's calendar time goes, per activity, today and with the agents (days per tender)."""
    order: dict[str, int] = {}
    for evs in cases.values():
        for e in evs:
            order.setdefault(e.activity, len(order))
    n = max(1, len(cases))
    rows = []
    for activity in sorted(base["per_activity"], key=lambda a: order.get(a, 99)):
        b = base["per_activity"][activity]
        a = after["per_activity"].get(activity, [0.0, 0.0])
        rows.append(
            {
                "activity": activity,
                "before": {"work": round(b[0] / n / 24, 2), "wait": round(b[1] / n / 24, 2)},
                "after": {"work": round(a[0] / n / 24, 2), "wait": round(a[1] / n / 24, 2)},
            }
        )
    return [r for r in rows if r["before"]["work"] + r["before"]["wait"] >= 0.01]


def what_if(
    cases: dict[str, list[Event]], readiness: dict[str, dict[str, Any]], scope: list[str] | None = None, seed: int = 7
) -> dict[str, Any]:
    factors = effort_factors(readiness, scope)
    base = replay(cases, {})
    after = replay(cases, factors)
    ids = list(base["lead_days"])
    observed = [_hours(cases[c][0].start, cases[c][-1].complete) / 24 for c in ids]
    saved_by_role = {
        r: round(base["hours_by_role"].get(r, 0) - after["hours_by_role"].get(r, 0), 1) for r in base["hours_by_role"]
    }
    # Bootstrap over tenders: how sure is the change in the median lead time?
    rnd = random.Random(seed)
    diffs = []
    for _ in range(settings()["value"]["bootstrap_samples"]):
        sample = [rnd.choice(ids) for _ in ids]
        diffs.append(st.median(base["lead_days"][c] for c in sample) - st.median(after["lead_days"][c] for c in sample))
    return {
        "factors": {k: round(v, 3) for k, v in sorted(factors.items())},
        "model_check": {
            "observed_median_days": round(st.median(observed), 1),
            "replayed_median_days": round(st.median(base["lead_days"].values()), 1),
        },
        "lead_time_days": {
            "before": round(st.median(base["lead_days"].values()), 1),
            "after": round(st.median(after["lead_days"].values()), 1),
            "saved_low": round(_pct(diffs, 0.05), 1),
            "saved_high": round(_pct(diffs, 0.95), 1),
        },
        "timeline": _timeline(cases, base, after),
        "hours_saved_by_role": saved_by_role,
        "hours_saved": round(sum(saved_by_role.values()), 1),
        "period_days": round(
            _hours(
                min(e.start for evs in cases.values() for e in evs),
                max(e.complete for evs in cases.values() for e in evs),
            )
            / 24
        ),
    }


def compare_live(
    history: dict[str, list[Event]], live: dict[str, list[Event]], factors: dict[str, float]
) -> list[dict[str, Any]]:
    """After go-live: how much each activity's effort really changed, next to what the scoping projected."""

    def means(cases: dict[str, list[Event]]) -> dict[str, float]:
        acc: dict[str, list[float]] = defaultdict(list)
        for evs in cases.values():
            for e in evs:
                if e.work_hours > 0:
                    acc[e.activity].append(e.work_hours)
        return {a: st.fmean(v) for a, v in acc.items()}

    before, after = means(history), means(live)
    rows = []
    for activity in sorted(before):
        if activity not in after:
            continue
        actual = after[activity] / before[activity]
        projected = factors.get(activity, 1.0)
        rows.append(
            {
                "activity": activity,
                "hours_before": round(before[activity], 2),
                "hours_after": round(after[activity], 2),
                "actual_factor": round(actual, 2),
                "projected_factor": round(projected, 2),
                "gap": round(actual - projected, 2),
            }
        )
    return rows


def log_path(customer: str, live: bool = False, base: Path | None = None) -> Path:
    return (base or data_dir()) / "customers" / customer / ("quote_process_live.csv" if live else "quote_process.csv")
