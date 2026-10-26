"""Held-out sets: tenders written by someone who never saw the code, with their answer keys.

The first run of a set is written to reports/heldout/<set>/first_run.json once and never rewritten; later runs
go to latest.json. A set whose failures were studied is marked a regression set (heldout/<set>/STATUS) and a new
set is written from heldout/WRITING_TENDERS.md.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from .config import root
from .evaluate import readiness, score
from .pipeline import analyse


def run(set_name: str, base: Path | None = None) -> dict[str, Any]:
    base = base or root()
    folder = base / "heldout" / set_name
    if not folder.exists():
        raise FileNotFoundError(folder)
    status = (folder / "STATUS").read_text().strip() if (folder / "STATUS").exists() else "heldout"
    result: dict[str, Any] = {
        "set": set_name,
        "status": status,
        "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "customers": {},
    }
    for cust in sorted(p for p in folder.iterdir() if p.is_dir()):
        keys = {
            p.name.removesuffix(".answer.json"): json.loads(p.read_text(encoding="utf-8"))
            for p in cust.glob("*.answer.json")
        }
        analyses = [analyse(t, cust.name) for t in sorted(p for p in cust.iterdir() if p.is_dir() and p.name in keys)]
        sc = score(analyses, keys)
        result["customers"][cust.name] = {
            "tenders": sc.tenders,
            "metrics": {k: v.as_dict() for k, v in sorted(sc.counts.items())},
            "readiness": {
                k: {kk: vv for kk, vv in v.items() if kk in ("level", "right", "of", "rate", "lower_bound")}
                for k, v in readiness(sc).items()
            },
            "misses": [m.__dict__ for m in sc.misses],
        }
    reports = base / "reports" / "heldout" / set_name
    reports.mkdir(parents=True, exist_ok=True)
    first = reports / "first_run.json"
    text = json.dumps(result, ensure_ascii=False, indent=1, default=str)
    if not first.exists():
        first.write_text(text, encoding="utf-8")
        result["recorded_as_first_run"] = True
    (reports / "latest.json").write_text(text, encoding="utf-8")
    return result
