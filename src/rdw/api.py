"""HTTP API for the console and for other tools (CRM widgets, notebooks). JSON in, JSON out; problem details on errors."""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import store
from .config import agents, customer, data_dir, root, settings
from .outputs import clarification_letter, compliance_matrix
from .pipeline import analyse
from .service import Workbench

ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@lru_cache
def workbench() -> Workbench:
    today = os.environ.get("RDW_TODAY")
    return Workbench(today=dt.date.fromisoformat(today) if today else None)


def require_token(request: Request) -> None:
    token = os.environ.get("RDW_API_TOKEN")
    if token and request.headers.get("authorization") != f"Bearer {token}":
        raise HTTPException(401, "a valid bearer token is required")


app = FastAPI(title="rfq-deployment-workbench", version="0.1.0", dependencies=[Depends(require_token)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("RDW_CORS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def problem(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        {"title": exc.detail, "status": exc.status_code},
        status_code=exc.status_code,
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", ()) if x != "body")
    return JSONResponse(
        {"title": "the request is not valid", "detail": f"{where}: {first.get('msg', 'invalid')}", "status": 422},
        status_code=422,
        media_type="application/problem+json",
    )


def _customer(cid: str) -> str:
    if not ID.match(cid) or cid not in workbench().customers():
        raise HTTPException(404, f"no customer {cid}")
    return cid


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "customers": len(workbench().customers()), "database": store.url().split("://")[0]}


@app.get("/api/agents")
def list_agents() -> dict[str, Any]:
    return agents()


@app.get("/api/portfolio")
def portfolio() -> dict[str, Any]:
    return workbench().portfolio()


@app.get("/api/heldout")
def heldout() -> list[dict[str, Any]]:
    return workbench().heldout()


@app.get("/api/customers/{cid}")
def deployment(cid: str) -> dict[str, Any]:
    wb = workbench()
    d = wb.deployment(_customer(cid))
    return {**d, "summary": wb.summary(cid, d)}


@app.get("/api/customers/{cid}/discovery")
def discovery(cid: str) -> dict[str, Any]:
    return workbench().discovery(_customer(cid))


@app.get("/api/customers/{cid}/readiness")
def readiness(cid: str) -> dict[str, Any]:
    ev = workbench().evaluation(_customer(cid))
    labels = {k: spec.label for k, spec in customer(cid).kinds.items()}
    return {**ev, "misses": ev["misses"][:200], "bar": settings()["readiness"], "kind_labels": labels}


class ValueQuery(BaseModel):
    scope: list[str] | None = None
    assumptions: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/customers/{cid}/value")
def value(cid: str, q: ValueQuery) -> dict[str, Any]:
    wb = workbench()
    _customer(cid)
    if q.scope is not None and not set(q.scope) <= set(agents()):
        raise HTTPException(422, "unknown agent in scope")
    return {**wb.value(cid, q.scope, q.assumptions), "what_if": wb.what_if(cid, q.scope)}


@app.put("/api/customers/{cid}/assumptions")
def put_assumptions(cid: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"hourly_cost", "hours_per_person_year", "annual_fee", "volume_growth"}
    if not set(payload) <= allowed:
        raise HTTPException(422, f"assumptions are limited to {sorted(allowed)}")
    return store.set_assumptions(_customer(cid), payload)


@app.get("/api/customers/{cid}/live")
def live(cid: str) -> dict[str, Any]:
    result = workbench().live(_customer(cid))
    if result is None:
        raise HTTPException(404, "this customer is not live yet")
    return result


@app.get("/api/customers/{cid}/tenders")
def tenders(cid: str) -> list[dict[str, Any]]:
    wb = workbench()
    reviewed: dict[str, int] = {}
    for r in store.list_reviews(_customer(cid)):
        reviewed[r["tender"]] = reviewed.get(r["tender"], 0) + 1
    return [
        {
            "id": a.tender_id,
            "subject": a.subject,
            "buyer": a.buyer,
            "due": a.due,
            "language": a.language,
            "decision": a.bid.decision,
            "variant": a.configuration.variant,
            "requirements": len(a.requirements),
            "red_flags": len(a.red_flags),
            "knockouts": len(a.bid.knockouts),
            "reviewed": reviewed.get(a.tender_id, 0),
        }
        for a in wb.analyses(cid)
    ]


def _tender(cid: str, tid: str):  # type: ignore[no-untyped-def]
    if not ID.match(tid):
        raise HTTPException(404, "no such tender")
    a = workbench().tender(_customer(cid), tid)
    if a is None:
        raise HTTPException(404, f"no tender {tid}")
    return a


@app.get("/api/customers/{cid}/tenders/{tid}")
def tender(cid: str, tid: str) -> dict[str, Any]:
    a = _tender(cid, tid)
    return {**a.model_dump(), "reviews": store.list_reviews(cid, tid)}


class ReviewIn(BaseModel):
    verdict: str = Field(pattern="^(comply|clarify|deviate)$")
    comment: str = Field(default="", max_length=2000)
    reviewer: str = Field(min_length=1, max_length=128)


@app.post("/api/customers/{cid}/tenders/{tid}/requirements/{rid}/review")
def review(cid: str, tid: str, rid: str, body: ReviewIn) -> dict[str, Any]:
    a = _tender(cid, tid)
    req = next((r for r in a.requirements if r.id == rid), None)
    if req is None:
        raise HTTPException(404, f"no requirement {rid}")
    return store.save_review(cid, tid, rid, req.kind, req.verdict, body.verdict, body.comment, body.reviewer)


@app.get("/api/customers/{cid}/tenders/{tid}/compliance.xlsx")
def matrix(cid: str, tid: str) -> Response:
    a = _tender(cid, tid)
    reviews = {r["requirement"]: r["verdict"] for r in store.list_reviews(cid, tid)}
    return Response(
        compliance_matrix(a, reviews),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"content-disposition": f'attachment; filename="{tid}-compliance.xlsx"'},
    )


@app.get("/api/customers/{cid}/tenders/{tid}/letter", response_class=PlainTextResponse)
def letter(cid: str, tid: str) -> str:
    a = _tender(cid, tid)
    return clarification_letter(a, customer(cid).name)


@app.post("/api/customers/{cid}/inbox")
async def upload(cid: str, files: Annotated[list[UploadFile], File()]) -> dict[str, Any]:
    """Analyses a new tender (PDF, Excel, e-mail, text) without adding it to the scored history."""
    _customer(cid)
    folder = data_dir() / "inbox" / cid / f"IN-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True)
    try:
        for f in files[:10]:
            name = Path(f.filename or "file").name
            if Path(name).suffix.lower() not in (".pdf", ".xlsx", ".eml", ".txt", ".md"):
                raise HTTPException(415, f"{name}: send PDF, Excel, e-mail or text")
            data = await f.read()
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(413, f"{name} is larger than 20 MB")
            (folder / name).write_bytes(data)
        return analyse(folder, cid).model_dump()
    except HTTPException:
        shutil.rmtree(folder, ignore_errors=True)
        raise


@app.get("/api/customers/{cid}/steerco")
def steerco(cid: str) -> dict[str, Any]:
    return workbench().steerco(_customer(cid))


class DecisionIn(BaseModel):
    decision: str = Field(min_length=3, max_length=2000)
    by: str = Field(min_length=1, max_length=128)


@app.post("/api/customers/{cid}/decisions")
def decide(cid: str, body: DecisionIn) -> dict[str, Any]:
    return store.add_decision(_customer(cid), body.decision, body.by)


web = Path(os.environ.get("RDW_WEB", root() / "web" / "dist"))
if web.exists():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=web / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def console(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404, "no such endpoint")
        file = (web / path).resolve()
        if path and file.is_file() and web.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(web / "index.html")  # the console routes on the client
