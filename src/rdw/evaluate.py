"""Scoring the agents against the customer's own answer key: the compliance matrices and bid decisions their
sales engineers produced for past tenders. The only module that reads data/truth.

Readiness per agent comes from the lower bound of a Wilson interval, so 9 of 10 right on a small pilot does not
read as 90 %. Every miss is kept with its cause, because the cause decides who fixes it: the platform (vocabulary,
parsing) or the deployment (the customer's capability profile).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import agents, data_dir, settings
from .models import TenderAnalysis


def _norm_text(s: str) -> str:
    s = s.lower().replace("−", "-").replace("–", "-")
    s = re.sub(r"^\d+(\.\d+)*\s+", "", s)
    return re.sub(r"[^\wäöüß%‰+.-]+", " ", s).strip()


def similarity(a: str, b: str) -> float:
    na, nb = _norm_text(a), _norm_text(b)
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    return len(ta & tb) / len(ta | tb)


def wilson_lower(k: int, n: int, confidence: float = 0.95) -> float:
    if n == 0:
        return 0.0
    z = {0.9: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    p = k / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / (1 + z * z / n))


@dataclass
class Count:
    k: int = 0
    n: int = 0

    def add(self, ok: bool) -> None:
        self.n += 1
        self.k += int(ok)

    @property
    def rate(self) -> float:
        return self.k / self.n if self.n else 0.0

    def as_dict(self) -> dict[str, Any]:
        conf = settings()["readiness"]["confidence"]
        return {
            "right": self.k,
            "of": self.n,
            "rate": round(self.rate, 4),
            "lower_bound": round(wilson_lower(self.k, self.n, conf), 4),
        }


@dataclass
class Miss:
    tender: str
    agent: str
    cause: str  # vocabulary | value | capability_profile | norm_profile | rule | noise
    owner: str  # platform | deployment
    text: str
    expected: Any
    got: Any


@dataclass
class Scorecard:
    customer: str
    tenders: int
    counts: dict[str, Count] = field(default_factory=dict)
    misses: list[Miss] = field(default_factory=list)

    def c(self, name: str) -> Count:
        return self.counts.setdefault(name, Count())


def _same_value(expected: Any, got: Any) -> bool:
    if expected is None:
        return got in (None, "unlimited")
    if isinstance(expected, (int, float)) and isinstance(got, (int, float)) and not isinstance(expected, bool):
        return abs(float(expected) - float(got)) < 1e-6 * max(1, abs(float(expected))) + 0.05
    if isinstance(expected, list) and isinstance(got, list):
        return len(expected) == len(got) and all(_same_value(a, b) for a, b in zip(expected, got, strict=True))
    return str(expected).lower().replace(" ", "") == str(got).lower().replace(" ", "")


def load_truth(customer: str, tender_id: str, base: Path | None = None) -> dict[str, Any] | None:
    path = (base or data_dir()) / "truth" / customer / "tenders" / f"{tender_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def score(analyses: list[TenderAnalysis], truths: dict[str, dict[str, Any]]) -> Scorecard:
    if not analyses:
        return Scorecard("", 0)
    sc = Scorecard(analyses[0].customer, 0)
    threshold = settings()["evaluation"]["match_jaccard"]
    for a in analyses:
        t = truths.get(a.tender_id)
        if t is None:
            continue
        sc.tenders += 1
        used: set[str] = set()
        for tr in t["requirements"]:
            doc = tr["doc"]
            best, best_sim = None, 0.0
            for r in a.requirements:
                if r.id in used or (r.source.doc != doc and not (doc == "spec" and r.source.doc in ("spec",))):
                    continue
                sim = similarity(tr["text"], r.source.text)
                if sim > best_sim:
                    best, best_sim = r, sim
            matched = best is not None and best_sim >= threshold
            sc.c("requirement_recall").add(matched)
            if tr["red_flag"]:
                sc.c("red_flag_recall").add(bool(matched and best and best.red_flag))
            if not matched or best is None:
                sc.misses.append(
                    Miss(a.tender_id, "requirement_extraction", "vocabulary", "platform", tr["text"], tr["kind"], None)
                )
                sc.c("verdict_accuracy").add(False)
                continue
            used.add(best.id)
            kind_ok = best.kind == tr["kind"]
            sc.c("kind_accuracy").add(kind_ok)
            if tr["kind"] not in ("procedural",) and tr["value"] is not None:
                value_ok = kind_ok and _same_value(tr["value"], best.value)
                sc.c("value_accuracy").add(value_ok)
            else:
                value_ok = kind_ok
            sc.c("priority_accuracy").add(best.priority == tr["priority"])
            verdict_ok = best.verdict == tr["verdict"]
            sc.c("verdict_accuracy").add(verdict_ok)
            if not verdict_ok:
                if not kind_ok:
                    cause, owner = "vocabulary", "platform"
                elif not value_ok:
                    cause, owner = "value", "platform"
                elif tr["kind"] == "norm":
                    cause, owner = "norm_profile", "deployment"
                else:
                    cause, owner = "capability_profile", "deployment"
                sc.misses.append(
                    Miss(
                        a.tender_id,
                        "technical_documentation",
                        cause,
                        owner,
                        tr["text"],
                        {"kind": tr["kind"], "value": tr["value"], "verdict": tr["verdict"]},
                        {"kind": best.kind, "value": best.value, "verdict": best.verdict},
                    )
                )
        truth_texts = [tr["text"] for tr in t["requirements"]]
        for r in a.requirements:
            noise = r.id not in used and all(similarity(x, r.source.text) < threshold for x in truth_texts)
            sc.c("requirement_precision").add(not noise)
            if r.red_flag:
                sc.c("red_flag_precision").add(
                    r.id in used
                    and any(
                        tr["red_flag"] and similarity(tr["text"], r.source.text) >= threshold
                        for tr in t["requirements"]
                    )
                )
            if noise:
                sc.misses.append(
                    Miss(a.tender_id, "requirement_extraction", "noise", "platform", r.source.text, None, r.kind)
                )
        found_norms = {n.norm.replace(" ", "").lower(): n for n in a.norms}
        for norm, status in t["norms"].items():
            hit = found_norms.get(norm.replace(" ", "").lower())
            sc.c("norm_recall").add(hit is not None)
            if hit is not None:
                ok = hit.status == status
                sc.c("norm_status_accuracy").add(ok)
                if not ok:
                    sc.misses.append(
                        Miss(a.tender_id, "norms_report", "norm_profile", "deployment", norm, status, hit.status)
                    )
            else:
                sc.misses.append(Miss(a.tender_id, "norms_report", "vocabulary", "platform", norm, status, None))
        truth_norms = {n.replace(" ", "").lower() for n in t["norms"]}
        for key in found_norms:
            sc.c("norm_precision").add(key in truth_norms)
        decision = "bid" if a.bid.decision in ("bid", "bid_with_conditions") else "no_bid"
        sc.c("bid_accuracy").add(decision == t["bid"])
        sc.c("unsafe_bid_avoided").add(not (decision == "bid" and t["bid"] == "no_bid"))
        if decision != t["bid"]:
            sc.misses.append(Miss(a.tender_id, "bid_no_bid", "rule", "platform", a.subject, t["bid"], a.bid.decision))
        if t["variant"] is not None:
            ok = a.configuration.variant == t["variant"]
            sc.c("variant_accuracy").add(ok)
            if not ok:
                sc.misses.append(
                    Miss(
                        a.tender_id,
                        "configuration",
                        "rule",
                        "platform",
                        a.subject,
                        t["variant"],
                        a.configuration.variant,
                    )
                )
    return sc


LEVELS = ("automate", "assist", "not_yet", "not_enough_evidence")


def readiness(sc: Scorecard) -> dict[str, dict[str, Any]]:
    cfg = settings()["readiness"]
    out = {}
    for name, agent in agents().items():
        count = sc.counts.get(agent["key_metric"], Count())
        lb = wilson_lower(count.k, count.n, cfg["confidence"])
        if count.n < cfg["min_items"]:
            level = "not_enough_evidence"
        elif lb >= cfg["automate"]:
            level = "automate"
        elif lb >= cfg["assist"]:
            level = "assist"
        else:
            level = "not_yet"
        misses = [m for m in sc.misses if m.agent == name]
        out[name] = {
            "label": agent["label"],
            "does": agent["does"],
            "metric": agent["key_metric"],
            **count.as_dict(),
            "level": level,
            "misses": len(misses),
            "fix_in_platform": sum(1 for m in misses if m.owner == "platform"),
            "fix_in_deployment": sum(1 for m in misses if m.owner == "deployment"),
        }
    return out


def evaluate_customer(customer: str, analyses: list[TenderAnalysis], base: Path | None = None) -> dict[str, Any]:
    truths = {a.tender_id: t for a in analyses if (t := load_truth(customer, a.tender_id, base)) is not None}
    sc = score(analyses, truths)
    return {
        "customer": customer,
        "tenders": sc.tenders,
        "metrics": {k: v.as_dict() for k, v in sorted(sc.counts.items())},
        "readiness": readiness(sc),
        "misses": [m.__dict__ for m in sc.misses],
    }
