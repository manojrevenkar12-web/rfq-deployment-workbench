"""The supplier's quote process as their CRM records it: one row per activity with who did it and when.

A small discrete-event simulation: tenders arrive at random, each activity needs a person of a role, people work
one tender at a time, buyers take days to answer questions. Waiting emerges from capacity, so the bottleneck is a
property of the process, not a label in the data. The truth (where it really waits, and how much faster each
activity became after go-live) is written separately for checking.
"""

from __future__ import annotations

import csv
import datetime as dt
import heapq
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .profiles import Profile

ROLE = {
    "Qualify": "sales",
    "Read requirements": "sales_engineering",
    "Technical review": "engineering",
    "Clarify with buyer": "sales_engineering",
    "Buyer answer": "buyer",
    "Norms check": "quality",
    "Commercial review": "legal",
    "Configure and price": "sales_engineering",
    "Write documentation": "sales_engineering",
    "Approve": "management",
    "Submitted": "sales",
    "No bid": "sales",
}

# Calendar hours per hour of work: people work about 40 of 168 hours a week on tenders.
CALENDAR_PER_WORK_HOUR = 168 / 40

# How agents changed each activity's effort after go-live (truth; the workbench estimates these on its own).
AFTER_GO_LIVE = {
    "Read requirements": 0.3,
    "Norms check": 0.35,
    "Commercial review": 0.55,
    "Configure and price": 0.75,
    "Write documentation": 0.45,
}


@dataclass
class Step:
    activity: str
    work_hours: float  # zero for milestones and buyer answers
    external_hours: float = 0.0  # calendar hours waited on someone outside (the buyer)


def _lognormal(rnd: random.Random, mean: float, cv: float) -> float:
    sigma = math.sqrt(math.log(1 + cv * cv))
    mu = math.log(mean) - sigma * sigma / 2
    return rnd.lognormvariate(mu, sigma)


def plan_case(p: Profile, rnd: random.Random, speedup: dict[str, float] | None = None) -> tuple[list[Step], int]:
    proc = p.process
    pages = max(4, int(_lognormal(rnd, {"rail": 45, "charging": 25, "fire": 60}[p.domain], 0.6)))
    size = math.sqrt(pages / {"rail": 45, "charging": 25, "fire": 60}[p.domain])

    def work(activity: str, factor: float = 1.0) -> Step:
        mean, cv = proc.service_hours[activity]
        f = (speedup or {}).get(activity, 1.0)
        scale = (
            size if activity in ("Read requirements", "Technical review", "Write documentation", "Norms check") else 1.0
        )
        return Step(activity, _lognormal(rnd, mean * scale * factor * f, cv))

    steps = [work("Qualify")]
    if rnd.random() < proc.no_bid_rate * 0.5:
        return [*steps, Step("No bid", 0)], pages
    steps += [work("Read requirements"), work("Technical review")]
    rounds = 0
    while rnd.random() < proc.clarification_rate * (0.5**rounds) and rounds < 3:
        steps += [
            work("Clarify with buyer"),
            Step("Buyer answer", 0, _lognormal(rnd, *proc.buyer_answer_hours)),
            work("Technical review", 0.5),
        ]
        rounds += 1
    if rnd.random() < proc.no_bid_rate * 0.5:
        return [*steps, Step("No bid", 0)], pages
    steps += [
        work("Norms check"),
        work("Commercial review"),
        work("Configure and price"),
        work("Write documentation"),
        work("Approve"),
        Step("Submitted", 0),
    ]
    return steps, pages


def simulate(
    p: Profile,
    rnd: random.Random,
    start: dt.datetime,
    days: int,
    speedup: dict[str, float] | None = None,
    prefix: str = "",
) -> list[dict[str, str]]:
    """Runs the process for `days` and returns the event log rows of every case that finished."""
    proc = p.process
    people = {
        role: [f"{role.replace('_', ' ').title()} {i + 1}" for i in range(n)] for role, n in proc.resources.items()
    }
    free_at = {role: [0.0] * len(names) for role, names in people.items()}
    horizon = days * 24.0
    rate = proc.tenders_per_year / (365 * 24)
    t = 0.0
    arrivals: list[float] = []
    while True:
        t += rnd.expovariate(rate)
        if t > horizon * 0.85:  # leave time for the last tenders to finish
            break
        arrivals.append(t)

    cases: list[dict[str, Any]] = []
    for i, at in enumerate(arrivals):
        steps, pages = plan_case(p, rnd, speedup)
        cases.append(
            {"id": f"{prefix}{p.id[:2].upper()}-Q{i + 1:04d}", "steps": steps, "pages": pages, "ready": at, "next": 0}
        )

    # Event queue of (time ready for the next step, sequence, case index); roles serve in order of readiness.
    queue = [(c["ready"], i, i) for i, c in enumerate(cases)]
    heapq.heapify(queue)
    rows: list[dict[str, Any]] = []
    seq = len(cases)

    def stamp(h: float) -> str:
        return (start + dt.timedelta(hours=h)).isoformat(timespec="minutes")

    while queue:
        ready, _, ci = heapq.heappop(queue)
        c = cases[ci]
        step: Step = c["steps"][c["next"]]
        role = ROLE[step.activity]
        if step.activity == "Buyer answer":
            begin, end, who = ready + step.external_hours, ready + step.external_hours, "Buyer"
        elif step.work_hours == 0:
            begin = end = ready
            who = people["sales"][0]
        else:
            slots = free_at[role]
            k = min(range(len(slots)), key=lambda j: slots[j])
            begin = max(ready, slots[k])
            end = begin + step.work_hours * CALENDAR_PER_WORK_HOUR
            slots[k] = end
            who = people[role][k]
        rows.append(
            {
                "case_id": c["id"],
                "activity": step.activity,
                "resource": who,
                "role": role,
                "start": stamp(begin),
                "complete": stamp(end),
                "work_hours": f"{step.work_hours:.2f}",
                "pages": str(c["pages"]),
                "_end": end,
            }
        )
        c["next"] += 1
        if c["next"] < len(c["steps"]):
            seq += 1
            heapq.heappush(queue, (end, seq, ci))
    done = {r["case_id"] for r in rows if r["activity"] in ("Submitted", "No bid") and r["_end"] <= horizon}
    out = [r for r in rows if r["case_id"] in done]
    for r in out:
        del r["_end"]
    out.sort(key=lambda r: (r["start"], r["case_id"]))
    return out


def write_log(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["case_id", "activity", "resource", "role", "start", "complete", "work_hours", "pages"]
        )
        w.writeheader()
        w.writerows(rows)
