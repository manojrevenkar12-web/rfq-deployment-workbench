from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(world: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import os

    from rdw import api, store

    monkeypatch.setenv("RDW_DATA", str(world))
    monkeypatch.setenv("RDW_TODAY", "2026-10-26")
    monkeypatch.setenv(
        "RDW_DATABASE_URL", os.environ.get("RDW_TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'api.db'}"
    )
    store.reset()
    api.workbench.cache_clear()
    return TestClient(api.app)


def test_portfolio_and_customer(client: TestClient) -> None:
    p = client.get("/api/portfolio").json()
    assert len(p["customers"]) == 3
    d = client.get("/api/customers/voltaro").json()
    assert d["stage"] == "scale" and d["summary"]


def test_unknown_things_are_404_problems(client: TestClient) -> None:
    for url in (
        "/api/customers/nobody",
        "/api/customers/voltaro/tenders/XX-1",
        "/api/customers/brandt/live",
        "/api/customers/../etc/tenders",
    ):
        r = client.get(url)
        assert r.status_code == 404, url


def test_review_flow_and_compliance_matrix(client: TestClient) -> None:
    tid = client.get("/api/customers/gleiswerk/tenders").json()[0]["id"]
    t = client.get(f"/api/customers/gleiswerk/tenders/{tid}").json()
    rid = t["requirements"][0]["id"]
    r = client.post(
        f"/api/customers/gleiswerk/tenders/{tid}/requirements/{rid}/review",
        json={"verdict": "deviate", "comment": "we cannot", "reviewer": "Sabine"},
    )
    assert r.status_code == 200
    assert client.get(f"/api/customers/gleiswerk/tenders/{tid}").json()["reviews"][0]["verdict"] == "deviate"
    bad = client.post(
        f"/api/customers/gleiswerk/tenders/{tid}/requirements/{rid}/review", json={"verdict": "maybe", "reviewer": "x"}
    )
    assert bad.status_code == 422
    assert bad.headers["content-type"].startswith("application/problem+json")
    assert bad.json()["detail"].startswith("verdict")
    x = client.get(f"/api/customers/gleiswerk/tenders/{tid}/compliance.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_value_scope_and_assumptions(client: TestClient) -> None:
    full = client.post("/api/customers/gleiswerk/value", json={}).json()
    one = client.post("/api/customers/gleiswerk/value", json={"scope": ["requirement_extraction"]}).json()
    assert one["hours_per_year"] < full["hours_per_year"]
    assert client.post("/api/customers/gleiswerk/value", json={"scope": ["teleport"]}).status_code == 422
    assert client.put("/api/customers/gleiswerk/assumptions", json={"annual_fee": 1}).status_code == 200
    assert client.post("/api/customers/gleiswerk/value", json={}).json()["assumptions"]["annual_fee"] == 1
    assert client.put("/api/customers/gleiswerk/assumptions", json={"discount": 1}).status_code == 422


def test_upload_a_new_tender(client: TestClient) -> None:
    text = (
        "# Leistungsbeschreibung: Beschaffung von Schnellladesäulen\nAuftraggeber: Stadtwerke Test\n\n"
        "2 Technische Anforderungen\n2.1 Die Ladeleistung je Ladepunkt muss mindestens 480 kW betragen.\n"
    ).encode()
    r = client.post("/api/customers/voltaro/inbox", files={"files": ("spec.md", text, "text/markdown")})
    assert r.status_code == 200
    assert r.json()["bid"]["decision"] == "no_bid"
    assert (
        client.post(
            "/api/customers/voltaro/inbox", files={"files": ("x.exe", b"MZ", "application/octet-stream")}
        ).status_code
        == 415
    )


def test_steerco_and_decisions(client: TestClient) -> None:
    assert "## KPIs" in client.get("/api/customers/brandt/steerco").json()["markdown"]
    client.post(
        "/api/customers/brandt/decisions",
        json={"decision": "Start with extraction and the letter.", "by": "Andrea Brandt"},
    )
    assert any(d["source"] == "workbench" for d in client.get("/api/customers/brandt").json()["decisions"])


def test_token_is_required_when_configured(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RDW_API_TOKEN", "s3cret")
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers={"authorization": "Bearer s3cret"}).status_code == 200


def test_timeline_adds_up_to_the_replayed_lead_time(client: TestClient) -> None:
    v = client.post("/api/customers/gleiswerk/value", json={}).json()
    timeline = v["what_if"]["timeline"]
    before = sum(r["before"]["work"] + r["before"]["wait"] for r in timeline)
    after = sum(r["after"]["work"] + r["after"]["wait"] for r in timeline)
    lead = v["what_if"]["lead_time_days"]
    assert after < before
    # the average tender against the median tender: close, not equal
    assert abs(before - lead["before"]) / lead["before"] < 0.35
    assert abs(after - lead["after"]) / lead["after"] < 0.35
    assert all(r["after"]["work"] <= r["before"]["work"] + 1e-9 for r in timeline)
