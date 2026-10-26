"""What the agents produce for one tender. Every finding carries its source, so a person can confirm it."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Verdict = Literal["comply", "clarify", "deviate"]
Severity = Literal["knockout", "major", "minor"]


class Source(BaseModel):
    doc: str  # spec | lv | eml (the file kind)
    file: str
    locator: str  # "page 2, 3.4" | "row 1.03" | "body"
    text: str


class Requirement(BaseModel):
    id: str
    source: Source
    kind: str  # a kind from the domain vocabulary, or "procedural" / "other"
    label: str
    value: Any = None
    unit: str | None = None
    priority: Literal["mandatory", "desirable"] = "mandatory"
    norms: list[str] = Field(default_factory=list)
    verdict: Verdict = "clarify"
    reason: str = ""
    red_flag: bool = False
    severity: Severity | None = None
    confidence: float = 1.0


class NormFinding(BaseModel):
    norm: str
    status: Literal["certified", "not_certified", "unknown"]
    cited_in: list[str]  # requirement ids


class BidRecommendation(BaseModel):
    decision: Literal["bid", "bid_with_conditions", "no_bid"]
    reasons: list[str]
    knockouts: list[str]  # requirement ids
    conditions: list[str]


class Configuration(BaseModel):
    variant: str | None
    reason: str


class TenderAnalysis(BaseModel):
    tender_id: str
    customer: str
    language: Literal["de", "en"]
    subject: str
    buyer: str | None
    due: str | None
    documents: list[str]
    requirements: list[Requirement]
    norms: list[NormFinding]
    bid: BidRecommendation
    configuration: Configuration

    @property
    def red_flags(self) -> list[Requirement]:
        return [r for r in self.requirements if r.red_flag]
