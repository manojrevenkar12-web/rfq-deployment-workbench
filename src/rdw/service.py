"""The workbench as one object: analyses, scores, discovery, value, deployment status, SteerCo pack, portfolio.

Results that take seconds (running every agent on every tender, replaying a year of quotes) are cached per
customer until the customer's data changes.
"""

from __future__ import annotations

import datetime as dt
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path
from threading import Lock
from typing import Any

from . import store
from .config import agents, customer, customer_ids, data_dir, deployment_config, settings
from .discovery import analyse_log, compare_live, effort_factors, load_log, log_path, what_if
from .evaluate import evaluate_customer
from .models import TenderAnalysis
from .pipeline import analyse, tender_folders
from .value import value_case


def _stamp(cid: str, base: Path) -> float:
    folder = base / "customers" / cid
    if not folder.exists():
        return 0.0
    return max((p.stat().st_mtime for p in folder.rglob("*") if p.is_file()), default=0.0)


class Workbench:
    def __init__(self, base: Path | None = None, today: dt.date | None = None):
        self.base = base or data_dir()
        self.today = today or dt.date.today()
        self._cache: dict[tuple[str, str], tuple[float, Any]] = {}
        self._lock = Lock()

    def _cached(self, cid: str, key: str, fn: Any) -> Any:
        stamp = _stamp(cid, self.base)
        with self._lock:
            hit = self._cache.get((cid, key))
            if hit and hit[0] == stamp:
                return hit[1]
        value = fn()
        with self._lock:
            self._cache[(cid, key)] = (stamp, value)
        return value

    # ------------------------------------------------------------------ per customer

    def customers(self) -> list[str]:
        return [c for c in customer_ids() if (self.base / "customers" / c).exists()]

    def analyses(self, cid: str) -> list[TenderAnalysis]:
        return self._cached(cid, "analyses", lambda: [analyse(f, cid) for f in tender_folders(cid, self.base)])

    def tender(self, cid: str, tender_id: str) -> TenderAnalysis | None:
        return next((a for a in self.analyses(cid) if a.tender_id == tender_id), None)

    def evaluation(self, cid: str) -> dict[str, Any]:
        return self._cached(cid, "evaluation", lambda: evaluate_customer(cid, self.analyses(cid), self.base))

    def discovery(self, cid: str) -> dict[str, Any]:
        return self._cached(cid, "discovery", lambda: analyse_log(load_log(log_path(cid, base=self.base))))

    def scope(self, cid: str) -> list[str]:
        return list(deployment_config(cid).get("scope", agents().keys()))

    def what_if(self, cid: str, scope: list[str] | None = None) -> dict[str, Any]:
        scope = scope if scope is not None else self.scope(cid)
        key = "what_if:" + ",".join(sorted(scope))
        return self._cached(
            cid, key, lambda: what_if(load_log(log_path(cid, base=self.base)), self.evaluation(cid)["readiness"], scope)
        )

    def value(
        self, cid: str, scope: list[str] | None = None, assumptions: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        agreed = {
            **(
                {"annual_fee": deployment_config(cid).get("contract", {}).get("annual_fee")}
                if deployment_config(cid).get("contract")
                else {}
            ),
            **store.get_assumptions(cid),
        }
        return value_case(self.what_if(cid, scope), {**agreed, **(assumptions or {})})

    def live(self, cid: str) -> dict[str, Any] | None:
        path = log_path(cid, live=True, base=self.base)
        if not path.exists():
            return None

        def run() -> dict[str, Any]:
            history, live = load_log(log_path(cid, base=self.base)), load_log(path)
            factors = effort_factors(self.evaluation(cid)["readiness"], self.scope(cid))
            return {
                "since": deployment_config(cid).get("go_live"),
                "discovery": analyse_log(live),
                "activities": compare_live(history, live, factors),
                "projected": self.what_if(cid),
            }

        return self._cached(cid, "live", run)

    # ------------------------------------------------------------------ deployment

    def kpis(self, cid: str) -> list[dict[str, Any]]:
        cfg = deployment_config(cid)
        ev = self.evaluation(cid)["metrics"]
        disc = self.discovery(cid)
        live = self.live(cid)
        wi = self.what_if(cid)
        amber = settings()["deployment"]["kpi_amber_share"]
        out = []
        for k in cfg.get("kpis", []):
            key = k["key"]
            actual: float | None
            basis = ""
            baseline = None
            if key in ("requirement_recall", "red_flag_recall"):
                actual, basis = ev.get(key, {}).get("rate"), f"scored on {self.evaluation(cid)['tenders']} past tenders"
            elif key == "lead_time_days":
                baseline = disc["lead_time_days"]["median"]
                if live:
                    actual, basis = live["discovery"]["lead_time_days"]["median"], "measured since go-live"
                else:
                    actual, basis = wi["lead_time_days"]["after"], "projected from the replay"
            elif key == "se_hours_per_tender":
                baseline = round(disc["work_hours_by_role"].get("sales_engineering", 0) / max(1, disc["submitted"]), 1)
                if live:
                    d = live["discovery"]
                    actual, basis = (
                        round(d["work_hours_by_role"].get("sales_engineering", 0) / max(1, d["submitted"]), 1),
                        "measured since go-live",
                    )
                else:
                    saved = wi["hours_saved_by_role"].get("sales_engineering", 0)
                    actual = round(
                        (disc["work_hours_by_role"].get("sales_engineering", 0) - saved) / max(1, disc["submitted"]), 1
                    )
                    basis = "projected from the replay"
            elif key == "engineering_wait_days":
                row = next((a for a in disc["activities"] if a["activity"] == "Technical review"), None)
                actual, basis = (round(row["wait_hours_mean"] / 24, 1) if row else None), "today, from the CRM export"
            elif key == "clarification_rounds":
                row = next((a for a in disc["activities"] if a["activity"] == "Clarify with buyer"), None)
                actual, basis = (round(row["count"] / disc["cases"], 2) if row else 0.0), "today, from the CRM export"
            elif key == "review_acceptance":
                actual, basis = store.review_stats(cid)["acceptance"], "reviews in the workbench"
            else:
                actual = None
            status = "unknown"
            if actual is not None:
                t = k["target"]
                if k["better"] == "higher":
                    status = "green" if actual >= t else "amber" if actual >= t * amber else "red"
                else:
                    status = "green" if actual <= t else "amber" if actual <= t / amber else "red"
            out.append({**k, "actual": actual, "baseline": baseline, "basis": basis, "status": status})
        return out

    def deployment(self, cid: str) -> dict[str, Any]:
        cfg = deployment_config(cid)
        c = customer(cid)
        milestones = []
        for m in cfg.get("milestones", []):
            planned = dt.date.fromisoformat(str(m["date"]))
            done = dt.date.fromisoformat(str(m["done"])) if m.get("done") else None
            state = "done" if done else ("overdue" if planned < self.today else "planned")
            milestones.append(
                {
                    "name": m["name"],
                    "planned": planned.isoformat(),
                    "done": done.isoformat() if done else None,
                    "state": state,
                    "days_late": (done - planned).days if done else max(0, (self.today - planned).days),
                }
            )
        kpis = self.kpis(cid)
        overdue = [m for m in milestones if m["state"] == "overdue"]
        health = (
            "red"
            if any(k["status"] == "red" for k in kpis) or any(m["days_late"] > 14 for m in overdue)
            else "amber"
            if any(k["status"] == "amber" for k in kpis) or overdue
            else "green"
        )
        decisions = [
            *({**d, "source": "plan"} for d in cfg.get("decisions", [])),
            *({**d, "source": "workbench"} for d in store.list_decisions(cid)),
        ]
        return {
            "customer": {"id": c.id, "name": c.name, "industry": c.industry, "location": c.location},
            "stage": cfg.get("stage"),
            "kickoff": str(cfg.get("kickoff")),
            "go_live": str(cfg.get("go_live")),
            "renewal": str(cfg.get("renewal")),
            "contract": cfg.get("contract", {}),
            "health": health,
            "scope": self.scope(cid),
            "not_in_scope": cfg.get("not_in_scope", {}),
            "stakeholders": cfg.get("stakeholders", []),
            "milestones": milestones,
            "kpis": kpis,
            "risks": cfg.get("risks", []),
            "decisions": [{**d, "date": str(d["date"])} for d in decisions],
            "next_steps": self.next_steps(cid, kpis, milestones),
        }

    def next_steps(
        self, cid: str, kpis: list[dict[str, Any]], milestones: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        steps = []
        for m in milestones:
            if m["state"] == "overdue":
                steps.append(
                    {
                        "kind": "milestone",
                        "who": "strategist",
                        "text": f"Overdue by {m['days_late']} days: {m['name']}. Agree a new date or remove it.",
                    }
                )
        ev = self.evaluation(cid)
        scope = self.scope(cid)
        for name, r in ev["readiness"].items():
            if name in scope and r["level"] in ("not_yet", "not_enough_evidence"):
                steps.append(
                    {
                        "kind": "readiness",
                        "who": "strategist + FDE",
                        "text": f"{r['label']} is {r['level'].replace('_', ' ')} ({r['right']}/{r['of']}). "
                        f"{r['fix_in_deployment']} misses are in the customer profile, {r['fix_in_platform']} in the platform.",
                    }
                )

        def what(m: dict[str, Any]) -> str:
            e = m["expected"]
            if isinstance(e, dict):
                return str(e["value"]) if e["kind"] == "norm" else e["kind"].replace("_", " ")
            return str(m["text"])

        profile = Counter((m["cause"], what(m)) for m in ev["misses"] if m["owner"] == "deployment")
        for (cause, item), n in profile.most_common(3):
            steps.append(
                {
                    "kind": "profile",
                    "who": "strategist",
                    "text": f"Fix the {cause.replace('_', ' ')} for {item}: the agents disagree with past decisions on {n} requirements.",
                }
            )
        live = self.live(cid)
        if live:
            in_scope = set()
            for name in scope:
                in_scope |= set(agents()[name]["activities"])
            for row in live["activities"]:
                if row["activity"] in in_scope and row["gap"] > 0.15:
                    steps.append(
                        {
                            "kind": "adoption",
                            "who": "champion",
                            "text": f"{row['activity']}: effort fell to {row['actual_factor']:.0%} of before, the plan was "
                            f"{row['projected_factor']:.0%}. Find out with the users why.",
                        }
                    )
        for k in kpis:
            if k["status"] == "red":
                steps.append(
                    {
                        "kind": "kpi",
                        "who": "strategist",
                        "text": f"{k['label']} is off target: {k['actual']} against {k['target']}.",
                    }
                )
        return steps

    def steerco(self, cid: str) -> dict[str, Any]:
        d = self.deployment(cid)
        v = self.value(cid)
        live = self.live(cid)
        lines = [
            f"# SteerCo: {d['customer']['name']}",
            "",
            f"{self.today.isoformat()} · stage {d['stage']} · health {d['health']}",
            "",
            "## Where we are",
            "",
            self.summary(cid, d, v),
            "",
            "## KPIs",
            "",
            "| KPI | Target | Now | Basis |",
            "| --- | --- | --- | --- |",
        ]
        for k in d["kpis"]:
            lines.append(
                f"| {k['label']} | {_fmt(k['target'], k['format'])} | {_fmt(k['actual'], k['format'])} ({k['status']}) | {k['basis']} |"
            )
        if live:
            lines += [
                "",
                "## Since go-live",
                "",
                "| Activity | Hours before | Hours now | Planned | Gap |",
                "| --- | --- | --- | --- | --- |",
            ]
            for r in live["activities"]:
                lines.append(
                    f"| {r['activity']} | {r['hours_before']} | {r['hours_after']} | {r['projected_factor']:.0%} | {r['gap']:+.0%} |"
                )
        lines += ["", "## Value", "", v["statement"], "", "## Decisions needed", ""]
        asks = [s for s in d["next_steps"] if s["kind"] in ("adoption", "readiness", "kpi")]
        lines += [f"- {s['text']}" for s in asks] or ["- None this time."]
        lines += ["", "## Risks", ""] + [
            f"- {r['risk']} Mitigation: {r['mitigation']} ({r['owner']})" for r in d["risks"]
        ]
        lines += ["", "## Milestones", ""] + [f"- {m['planned']} {m['name']}: {m['state']}" for m in d["milestones"]]
        return {
            "customer": cid,
            "date": self.today.isoformat(),
            "health": d["health"],
            "markdown": "\n".join(lines) + "\n",
            "asks": asks,
        }

    def summary(self, cid: str, d: dict[str, Any] | None = None, v: dict[str, Any] | None = None) -> str:
        d = d or self.deployment(cid)
        v = v or self.value(cid)
        ev = self.evaluation(cid)
        ready = [r["label"] for n, r in ev["readiness"].items() if n in d["scope"] and r["level"] == "automate"]
        stage = {"discovery": "In discovery", "pilot": "In the pilot", "scale": "Live"}.get(d["stage"], d["stage"])
        disc = self.discovery(cid)
        b = disc["bottleneck"]
        where = (
            f"waiting for buyers to answer questions ({b['wait_hours_per_case'] / 24:.1f} days per tender)"
            if b and b["kind"] == "external"
            else f"the queue for {b['activity'].lower()} ({b['wait_hours_per_case'] / 24:.1f} days per tender)"
            if b
            else "nowhere in particular"
        )
        return (
            f"{stage}. Of the agents in scope, {len(ready)} of {len(d['scope'])} meet the bar to work on their own "
            f"({', '.join(ready) or 'none yet'}). Tenders lose most time {where}. {v['statement']}"
        )

    # ------------------------------------------------------------------ across customers

    def portfolio(self) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        profile: list[dict[str, Any]] = []
        platform: defaultdict[tuple[str, str, str], dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "customers": set(), "examples": []}
        )
        kinds_by_customer: dict[str, set[str]] = {}
        for cid in self.customers():
            d = self.deployment(cid)
            ev = self.evaluation(cid)
            rows.append(
                {
                    "id": cid,
                    "name": d["customer"]["name"],
                    "industry": d["customer"]["industry"],
                    "stage": d["stage"],
                    "health": d["health"],
                    "renewal": d["renewal"],
                    "readiness": {n: r["level"] for n, r in ev["readiness"].items()},
                    "scope": d["scope"],
                    "tenders_scored": ev["tenders"],
                    "value_per_year": self.value(cid)["gross_per_year"],
                    "next_step": d["next_steps"][0]["text"] if d["next_steps"] else None,
                }
            )
            for m in ev["misses"]:
                if m["owner"] == "platform":
                    kind = (
                        m["expected"]["kind"]
                        if isinstance(m["expected"], dict)
                        else m["expected"]
                        if m["agent"] == "requirement_extraction"
                        else m["agent"]
                    )
                    key = (m["agent"], m["cause"], str(kind))
                    p = platform[key]
                    p["count"] += 1
                    p["customers"].add(cid)
                    if len(p["examples"]) < 2:
                        p["examples"].append(str(m["text"])[:140])
                else:
                    profile.append({"customer": cid, **m})
            kinds_by_customer[cid] = {r.kind for a in self.analyses(cid) for r in a.requirements}
        common = set.intersection(*kinds_by_customer.values()) if kinds_by_customer else set()
        backlog = sorted(
            (
                {
                    "agent": a,
                    "cause": c,
                    "kind": k,
                    "count": v["count"],
                    "customers": sorted(v["customers"]),
                    "examples": v["examples"],
                    "scales": len(v["customers"]) > 1,
                }
                for (a, c, k), v in platform.items()
            ),
            key=lambda x: (-len(x["customers"]), -x["count"]),
        )
        reviews = store.review_stats()
        corrected = sorted(
            ({"kind": k, **v} for k, v in reviews["by_kind"].items() if v["corrected"]), key=lambda x: -x["corrected"]
        )
        return {
            "customers": rows,
            "platform_backlog": backlog,
            "profile_fixes": profile[:50],
            "shared_kinds": sorted(common - {"other"}),
            "customer_specific_kinds": {c: sorted(k - common - {"other"}) for c, k in kinds_by_customer.items()},
            "reviews": {"acceptance": reviews["acceptance"], "corrected_by_kind": corrected},
            "playbook": self.playbook(),
        }

    def playbook(self) -> dict[str, Any]:
        lateness: dict[str, list[int]] = defaultdict(list)
        to_pilot, to_live = [], []
        for cid in self.customers():
            cfg = deployment_config(cid)
            kickoff = dt.date.fromisoformat(str(cfg["kickoff"]))
            for m in cfg.get("milestones", []):
                key = m["name"].split(" on ")[0].split(" for ")[0]
                if m.get("done"):
                    lateness[key].append(
                        (dt.date.fromisoformat(str(m["done"])) - dt.date.fromisoformat(str(m["date"]))).days
                    )
                    if m["name"].startswith("Pilot on"):
                        to_pilot.append((dt.date.fromisoformat(str(m["done"])) - kickoff).days)
                    if m["name"].startswith("Go-live"):
                        to_live.append((dt.date.fromisoformat(str(m["done"])) - kickoff).days)
        return {
            "days_kickoff_to_scored_pilot": st.median(to_pilot) if to_pilot else None,
            "days_kickoff_to_go_live": st.median(to_live) if to_live else None,
            "late_steps": sorted(
                ({"step": k, "median_days_late": st.median(v), "times": len(v)} for k, v in lateness.items()),
                key=lambda x: -x["median_days_late"],
            ),
        }


def _fmt(v: Any, fmt: str) -> str:
    if v is None:
        return "n/a"
    if fmt == "percent":
        return f"{v:.0%}"
    if fmt == "days":
        return f"{v} days"
    if fmt == "hours":
        return f"{v} h"
    return str(v)
