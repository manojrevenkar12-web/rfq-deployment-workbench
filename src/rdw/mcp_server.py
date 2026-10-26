"""MCP server: the workbench as tools for Claude (Claude Desktop, Claude Code), so a strategist can ask
"prepare tomorrow's SteerCo for Voltaro" and the answer is built from the same facts the console shows.

    claude mcp add rfq-workbench -- python -m rdw.mcp_server

Read-only except for recording a decision; every tool returns facts with their basis, not prose to trust.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # 1.x
    from mcp.server.fastmcp import FastMCP as Server  # type: ignore[no-redef,attr-defined,import-not-found,unused-ignore]

from . import store
from .service import Workbench

mcp = Server("rfq-deployment-workbench")
_wb: Workbench | None = None


def wb() -> Workbench:
    global _wb
    if _wb is None:
        today = os.environ.get("RDW_TODAY")
        _wb = Workbench(today=dt.date.fromisoformat(today) if today else None)
    return _wb


def _known(customer: str) -> str:
    if customer not in wb().customers():
        raise ValueError(f"unknown customer {customer!r}; known: {', '.join(wb().customers())}")
    return customer


@mcp.tool()
def list_customers() -> list[dict[str, Any]]:
    """Every customer with stage, health, renewal date and the first next step."""
    return [
        {k: c[k] for k in ("id", "name", "industry", "stage", "health", "renewal", "next_step")}
        for c in wb().portfolio()["customers"]
    ]


@mcp.tool()
def customer_brief(customer: str) -> dict[str, Any]:
    """One customer: summary, stakeholders (with notes on how to work with them), KPIs, milestones, risks,
    decisions and next steps. Use before any customer conversation."""
    d = wb().deployment(_known(customer))
    return {
        "summary": wb().summary(customer, d),
        **{
            k: d[k]
            for k in (
                "stage",
                "health",
                "scope",
                "not_in_scope",
                "stakeholders",
                "kpis",
                "milestones",
                "risks",
                "decisions",
                "next_steps",
            )
        },
    }


@mcp.tool()
def readiness(customer: str) -> dict[str, Any]:
    """Per agent: readiness level, the score on the customer's past tenders with its lower bound, and how many
    misses the platform must fix versus the customer's profile."""
    ev = wb().evaluation(_known(customer))
    return {"tenders_scored": ev["tenders"], "agents": ev["readiness"]}


@mcp.tool()
def process_bottleneck(customer: str) -> dict[str, Any]:
    """Where the customer's quote process loses time, from their CRM export: lead time, the activity tenders
    wait for most and whether that wait is internal (a queue) or external (the buyer)."""
    d = wb().discovery(_known(customer))
    return {
        k: d[k] for k in ("cases", "lead_time_days", "bottleneck", "internal_bottleneck", "utilisation", "rework_share")
    }


@mcp.tool()
def value_case(
    customer: str,
    scope: list[str] | None = None,
    hourly_cost: dict[str, float] | None = None,
    annual_fee: float | None = None,
) -> dict[str, Any]:
    """The value case for a scope of agents at current readiness, with the assumptions it used. Override
    hourly costs or the fee to answer "what if" questions from the customer's controller."""
    assumptions: dict[str, Any] = {}
    if hourly_cost:
        assumptions["hourly_cost"] = hourly_cost
    if annual_fee is not None:
        assumptions["annual_fee"] = annual_fee
    return wb().value(_known(customer), scope, assumptions)


@mcp.tool()
def adoption_since_go_live(customer: str) -> dict[str, Any] | str:
    """For a live customer: effort per activity before and after go-live next to what the scoping projected.
    Large positive gaps are where users have not changed how they work."""
    live = wb().live(_known(customer))
    return live["activities"] if live else "not live yet"  # type: ignore[return-value]


@mcp.tool()
def steerco_pack(customer: str) -> str:
    """The SteerCo pack as Markdown: status, KPIs with their basis, adoption, value, decisions needed, risks."""
    return wb().steerco(_known(customer))["markdown"]


@mcp.tool()
def platform_signals() -> dict[str, Any]:
    """Across customers: misses the core platform should fix (and whether they recur at more than one
    customer), requirement kinds every customer shares, reviewers' corrections, and the onboarding playbook."""
    p = wb().portfolio()
    return {k: p[k] for k in ("platform_backlog", "shared_kinds", "reviews", "playbook")}


@mcp.tool()
def heldout_results() -> list[dict[str, Any]]:
    """First runs on held-out tenders written by someone who never saw the code: the scores to quote.

    Counts per agent and cause only; the missed sentences stay out so nobody tunes the agents to them.
    """
    return wb().heldout()


@mcp.tool()
def tender_summary(customer: str, tender_id: str) -> dict[str, Any]:
    """One tender: bid recommendation with reasons, red flags with their source sentences, norms, variant."""
    a = wb().tender(_known(customer), tender_id)
    if a is None:
        raise ValueError(f"no tender {tender_id}")
    return {
        "subject": a.subject,
        "buyer": a.buyer,
        "due": a.due,
        "bid": a.bid.model_dump(),
        "variant": a.configuration.model_dump(),
        "red_flags": [
            {
                "label": r.label,
                "value": r.value,
                "severity": r.severity,
                "reason": r.reason,
                "source": f"{r.source.file}, {r.source.locator}: {r.source.text}",
            }
            for r in a.red_flags
        ],
        "norms": [n.model_dump() for n in a.norms],
    }


@mcp.tool()
def record_decision(customer: str, decision: str, by: str) -> dict[str, Any]:
    """Records a decision taken with the customer (SteerCo, call). Ask the user to confirm the wording first."""
    return store.add_decision(_known(customer), decision, by)


if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        import asyncio

        print(json.dumps(sorted(t.name for t in asyncio.run(mcp.list_tools())), indent=1))
    else:
        mcp.run()
