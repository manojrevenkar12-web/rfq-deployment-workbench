"""rdw: the workbench from the command line.

rdw analyse <tender folder> --customer voltaro     every agent on one tender (JSON)
rdw evaluate [--customer voltaro]                  agents scored against past decisions
rdw discover --customer brandt                     where the quote process loses time
rdw value --customer gleiswerk                     the value case at current readiness
rdw steerco --customer voltaro                     the SteerCo pack (Markdown)
rdw report                                         writes reports/*.md and reports/*.json
rdw heldout v1                                     scores a held-out set (first run recorded once)
rdw serve [--port 8000]                            the API and the console
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from .config import root


def _wb():  # type: ignore[no-untyped-def]
    from .service import Workbench

    today = os.environ.get("RDW_TODAY")
    return Workbench(today=dt.date.fromisoformat(today) if today else None)


def _print(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rdw", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyse")
    a.add_argument("folder", type=Path)
    a.add_argument("--customer", required=True)
    for name in ("evaluate", "discover", "value", "steerco"):
        p = sub.add_parser(name)
        p.add_argument("--customer", required=name != "evaluate")
    sub.add_parser("report")
    h = sub.add_parser("heldout")
    h.add_argument("set")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    if args.cmd == "analyse":
        from .pipeline import analyse

        _print(analyse(args.folder, args.customer).model_dump())
    elif args.cmd == "evaluate":
        wb = _wb()
        for cid in [args.customer] if args.customer else wb.customers():
            ev = wb.evaluation(cid)
            _print(
                {
                    "customer": cid,
                    "tenders": ev["tenders"],
                    "metrics": ev["metrics"],
                    "readiness": {k: v["level"] for k, v in ev["readiness"].items()},
                }
            )
    elif args.cmd == "discover":
        _print(_wb().discovery(args.customer))
    elif args.cmd == "value":
        _print(_wb().value(args.customer))
    elif args.cmd == "steerco":
        print(_wb().steerco(args.customer)["markdown"])
    elif args.cmd == "report":
        from .report import write_reports

        for path in write_reports(_wb(), root() / "reports"):
            print("wrote", path)
    elif args.cmd == "heldout":
        from .heldout import run

        result = run(args.set)
        for cid, r in result["customers"].items():
            m = r["metrics"]
            print(
                f"{cid}: {r['tenders']} tenders, requirements found {m.get('requirement_recall', {}).get('rate')}, "
                f"red flags found {m.get('red_flag_recall', {}).get('rate')}, verdicts right {m.get('verdict_accuracy', {}).get('rate')}"
            )
        if result.get("recorded_as_first_run"):
            print(f"recorded as the first run of {args.set}")
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("rdw.api:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
