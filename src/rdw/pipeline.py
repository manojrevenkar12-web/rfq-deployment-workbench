"""Runs every agent on one tender folder and returns a TenderAnalysis."""

from __future__ import annotations

from pathlib import Path

from .assess import configure, judge, norms_report, recommend
from .config import customer as load_customer
from .config import data_dir
from .extract import extract
from .ingest import read_tender
from .models import Requirement, Source, TenderAnalysis


def analyse(folder: Path, customer_id: str) -> TenderAnalysis:
    c = load_customer(customer_id)
    tender = read_tender(folder)
    found = extract(tender.segments, c.kinds, tender.language)
    reqs: list[Requirement] = []
    for i, f in enumerate(found, 1):
        spec = c.kinds.get(f.kind)
        label = (
            spec.label
            if spec
            else {"norm": "Norm", "procedural": "Bid procedure", "other": "Other"}.get(f.kind, f.kind)
        )
        unit = spec.unit if spec else None
        req = Requirement(
            id=f"{tender.id}-{i:02d}",
            source=Source(doc=f.segment.doc, file=f.segment.file, locator=f.segment.locator, text=f.segment.text),
            kind=f.kind,
            label=label,
            value=f.value,
            unit=unit,
            priority=f.priority,  # type: ignore[arg-type]
            norms=f.norms,
            confidence=round(f.confidence, 2),
        )
        reqs.append(judge(req, c))
    config = configure(reqs, tender.subject, c)
    return TenderAnalysis(
        tender_id=tender.id,
        customer=customer_id,
        language=tender.language,  # type: ignore[arg-type]
        subject=tender.subject,
        buyer=tender.buyer,
        due=tender.due,
        documents=tender.files,
        requirements=reqs,
        norms=norms_report(reqs, c),
        bid=recommend(reqs, config),
        configuration=config,
    )


def tender_folders(customer_id: str, base: Path | None = None) -> list[Path]:
    folder = (base or data_dir()) / "customers" / customer_id / "tenders"
    return sorted(p for p in folder.iterdir() if p.is_dir()) if folder.exists() else []


def analyse_all(customer_id: str, base: Path | None = None) -> list[TenderAnalysis]:
    return [analyse(f, customer_id) for f in tender_folders(customer_id, base)]
