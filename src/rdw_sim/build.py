"""rdw-sim: writes the three customers' data the way they would hand it over, and the truth beside it.

data/customers/<id>/tenders/<tender>/      spec.pdf, cover.eml, sometimes lv.xlsx
data/customers/<id>/quote_process.csv      a year of quote activities exported from the CRM
data/customers/<id>/quote_process_live.csv for a customer in production: the months since go-live
data/truth/<id>/tenders/<tender>.json      the answer key (past compliance matrices and bid decisions)
data/truth/<id>/process.json               where the process really waits; effect of the agents after go-live
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import shutil
from pathlib import Path

from .process import AFTER_GO_LIVE, simulate, write_log
from .profiles import PROFILES
from .tenders import TenderWriter, truth_json, write_documents

LIVE = {"voltaro": dt.date(2026, 8, 3)}  # customers already in production, and since when
HISTORY_START = dt.datetime(2025, 7, 1, 8, 0)


def build(root: Path, seed: int = 2026, quick: bool = False) -> dict[str, int]:
    data = root / "data"
    for sub in ("customers", "truth"):
        shutil.rmtree(data / sub, ignore_errors=True)
    counts: dict[str, int] = {}
    for cid, p in PROFILES.items():
        rnd = random.Random(f"{seed}-{cid}")
        writer = TenderWriter(p, rnd)
        n = max(6, p.pilot_tenders // 4) if quick else p.pilot_tenders
        day = dt.date(2026, 1, 12)
        for i in range(1, n + 1):
            day += dt.timedelta(days=rnd.randint(2, 6))
            truth, layout = writer.make(i, day)
            write_documents(truth, layout, data / "customers" / cid / "tenders" / truth.id, p, rnd)
            out = data / "truth" / cid / "tenders" / f"{truth.id}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(truth_json(truth), ensure_ascii=False, indent=1), encoding="utf-8")
        counts[cid] = n

        days = 120 if quick else 365
        log = simulate(p, random.Random(f"{seed}-{cid}-log"), HISTORY_START, days)
        write_log(log, data / "customers" / cid / "quote_process.csv")
        process_truth = {
            "bottleneck": p.process.bottleneck,
            "resources": p.process.resources,
            "cases": len({r["case_id"] for r in log}),
        }
        if cid in LIVE:
            live_start = dt.datetime.combine(LIVE[cid], dt.time(8, 0))
            live = simulate(
                p,
                random.Random(f"{seed}-{cid}-live"),
                live_start,
                60 if quick else 84,
                speedup=AFTER_GO_LIVE,
                prefix="L",
            )
            write_log(live, data / "customers" / cid / "quote_process_live.csv")
            process_truth["go_live"] = LIVE[cid].isoformat()
            process_truth["after_go_live_effort"] = AFTER_GO_LIVE
        (data / "truth" / cid / "process.json").write_text(json.dumps(process_truth, indent=1), encoding="utf-8")
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="rdw-sim", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--seed", default=2026, type=int)
    ap.add_argument("--quick", action="store_true", help="fewer tenders and a shorter history (tests)")
    args = ap.parse_args()
    counts = build(args.root, args.seed, args.quick)
    print("built", ", ".join(f"{k}: {v} tenders" for k, v in counts.items()))


if __name__ == "__main__":
    main()
