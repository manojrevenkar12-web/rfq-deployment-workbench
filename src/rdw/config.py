"""Configuration: domain vocabularies, customer capabilities, the agent catalogue and thresholds (config/*.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def root() -> Path:
    env = os.environ.get("RDW_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "workbench.yaml").exists():
            return parent
    return Path.cwd()


def data_dir() -> Path:
    return Path(os.environ.get("RDW_DATA", root() / "data"))


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class KindSpec:
    name: str
    label: str
    value: str  # number | range | enum | enum_number | bool | penalty | duration_months | duration_weeks | liability | language
    unit: str | None
    units: list[str]
    keywords_de: list[str]
    keywords_en: list[str]
    patterns: list[str]
    commercial: bool


@dataclass(frozen=True)
class Capability:
    op: str
    standard: Any
    limit: Any
    severity: str


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    domain: str
    industry: str
    location: str
    capabilities: dict[str, Capability]
    norms_certified: list[str]
    norms_not_certified: list[str]
    catalog: dict[str, Any]
    kinds: dict[str, KindSpec] = field(default_factory=dict)


@lru_cache
def settings() -> dict[str, Any]:
    return _load(root() / "config" / "workbench.yaml")


@lru_cache
def agents() -> dict[str, Any]:
    return _load(root() / "config" / "agents.yaml")["agents"]


@lru_cache
def domain_kinds(domain: str) -> dict[str, KindSpec]:
    kinds: dict[str, KindSpec] = {}
    for name in ("commercial", domain):
        raw = _load(root() / "config" / "domains" / f"{name}.yaml")["kinds"]
        for k, v in raw.items():
            kinds[k] = KindSpec(
                k,
                v["label"],
                v["value"],
                v.get("unit"),
                [u.lower() for u in v.get("units", [])],
                [w.lower() for w in v.get("keywords_de", [])],
                [w.lower() for w in v.get("keywords_en", [])],
                v.get("patterns", []),
                bool(v.get("commercial", False)),
            )
    return kinds


@lru_cache
def customer(cid: str) -> Customer:
    raw = _load(root() / "config" / "customers" / cid / "customer.yaml")
    caps = {k: Capability(v["op"], v["standard"], v["limit"], v["severity"]) for k, v in raw["capabilities"].items()}
    return Customer(
        raw["id"],
        raw["name"],
        raw["domain"],
        raw["industry"],
        raw["location"],
        caps,
        raw["norms"]["certified"],
        raw["norms"].get("not_certified", []),
        raw["catalog"],
        domain_kinds(raw["domain"]),
    )


def customer_ids() -> list[str]:
    return sorted(p.name for p in (root() / "config" / "customers").iterdir() if (p / "customer.yaml").exists())


def deployment_config(cid: str) -> dict[str, Any]:
    path = root() / "config" / "customers" / cid / "deployment.yaml"
    return _load(path) if path.exists() else {}
