"""What people add on top of the agents: reviews of agent answers, decisions taken in SteerCos, the value-case
assumptions a customer agreed to. SQLite by default, PostgreSQL in production (RDW_DATABASE_URL)."""

from __future__ import annotations

import datetime as dt
import json
import os
from functools import lru_cache
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from .config import data_dir

metadata = MetaData()

reviews = Table(
    "reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer", String(64), nullable=False, index=True),
    Column("tender", String(64), nullable=False),
    Column("requirement", String(96), nullable=False),
    Column("kind", String(64), nullable=False),
    Column("action", String(16), nullable=False),  # confirm | correct
    Column("agent_verdict", String(16), nullable=False),
    Column("verdict", String(16), nullable=False),
    Column("comment", Text, nullable=False, default=""),
    Column("reviewer", String(128), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("customer", "requirement", name="one_review_per_requirement"),
)

decisions = Table(
    "decisions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer", String(64), nullable=False, index=True),
    Column("date", String(10), nullable=False),
    Column("decision", Text, nullable=False),
    Column("by", String(128), nullable=False),
)

assumptions = Table(
    "assumptions",
    metadata,
    Column("customer", String(64), primary_key=True),
    Column("payload", Text, nullable=False),
    Column("updated", DateTime(timezone=True), nullable=False),
)


def url() -> str:
    return os.environ.get("RDW_DATABASE_URL") or f"sqlite:///{data_dir() / 'workbench.db'}"


@lru_cache
def engine_for(u: str) -> Engine:
    if u.startswith("sqlite:///"):
        from pathlib import Path

        Path(u.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(u, future=True, pool_pre_ping=True)
    metadata.create_all(eng)
    return eng


def engine() -> Engine:
    return engine_for(url())


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def save_review(
    customer: str,
    tender: str,
    requirement: str,
    kind: str,
    agent_verdict: str,
    verdict: str,
    comment: str,
    reviewer: str,
) -> dict[str, Any]:
    action = "confirm" if verdict == agent_verdict else "correct"
    row: dict[str, Any] = {
        "customer": customer,
        "tender": tender,
        "requirement": requirement,
        "kind": kind,
        "action": action,
        "agent_verdict": agent_verdict,
        "verdict": verdict,
        "comment": comment,
        "reviewer": reviewer,
        "at": now(),
    }
    with engine().begin() as c:
        c.execute(delete(reviews).where(reviews.c.customer == customer, reviews.c.requirement == requirement))
        c.execute(insert(reviews).values(**row))
    return {**row, "at": row["at"].isoformat()}


def list_reviews(customer: str, tender: str | None = None) -> list[dict[str, Any]]:
    q = select(reviews).where(reviews.c.customer == customer)
    if tender:
        q = q.where(reviews.c.tender == tender)
    with engine().connect() as c:
        return [{**r._mapping, "at": r.at.isoformat()} for r in c.execute(q.order_by(reviews.c.at))]


def review_stats(customer: str | None = None) -> dict[str, Any]:
    q = select(reviews.c.customer, reviews.c.kind, reviews.c.action, func.count()).group_by(
        reviews.c.customer, reviews.c.kind, reviews.c.action
    )
    if customer:
        q = q.where(reviews.c.customer == customer)
    out: dict[str, Any] = {"confirmed": 0, "corrected": 0, "by_kind": {}}
    with engine().connect() as c:
        for cust, kind, action, n in c.execute(q):
            key = "confirmed" if action == "confirm" else "corrected"
            out[key] += n
            k = out["by_kind"].setdefault(kind, {"confirmed": 0, "corrected": 0, "customers": set()})
            k[key] += n
            k["customers"].add(cust)
    for k in out["by_kind"].values():
        k["customers"] = sorted(k["customers"])
    total = out["confirmed"] + out["corrected"]
    out["acceptance"] = round(out["confirmed"] / total, 3) if total else None
    return out


def add_decision(customer: str, decision: str, by: str, date: str | None = None) -> dict[str, Any]:
    row = {"customer": customer, "date": date or now().date().isoformat(), "decision": decision, "by": by}
    with engine().begin() as c:
        c.execute(insert(decisions).values(**row))
    return row


def list_decisions(customer: str) -> list[dict[str, Any]]:
    with engine().connect() as c:
        return [
            dict(r._mapping)
            for r in c.execute(
                select(decisions).where(decisions.c.customer == customer).order_by(decisions.c.date, decisions.c.id)
            )
        ]


def get_assumptions(customer: str) -> dict[str, Any]:
    with engine().connect() as c:
        row = c.execute(select(assumptions.c.payload).where(assumptions.c.customer == customer)).first()
    return json.loads(row[0]) if row else {}


def set_assumptions(customer: str, payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True)
    with engine().begin() as c:
        done = c.execute(
            update(assumptions).where(assumptions.c.customer == customer).values(payload=text, updated=now())
        )
        if done.rowcount == 0:
            c.execute(insert(assumptions).values(customer=customer, payload=text, updated=now()))
    return payload


def reset(customer: str | None = None) -> None:
    with engine().begin() as c:
        for t in (reviews, decisions, assumptions):
            c.execute(delete(t) if customer is None else delete(t).where(t.c.customer == customer))
