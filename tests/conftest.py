from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def world(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A small simulated world (quick mode) in a temporary folder, built once per test session."""
    from rdw_sim.build import build

    base = tmp_path_factory.mktemp("world")
    build(base, seed=7, quick=True)
    return base / "data"


@pytest.fixture(scope="session")
def full_world() -> Path:
    """The full simulated world in data/ (built if missing), as the reports use it."""
    data = ROOT / "data"
    if not (data / "customers" / "voltaro" / "quote_process.csv").exists():
        from rdw_sim.build import build

        build(ROOT)
    return data


@pytest.fixture()
def wb(world: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    from rdw import store
    from rdw.service import Workbench

    monkeypatch.setenv(
        "RDW_DATABASE_URL", os.environ.get("RDW_TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    )
    store.reset()
    return Workbench(base=world, today=dt.date(2026, 10, 26))
