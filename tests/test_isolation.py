"""The workbench reads what a customer hands over. Only the scoring reads the answer key."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "rdw"
MAY_READ_TRUTH = {"evaluate.py"}


def test_only_the_scoring_reads_the_truth() -> None:
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.name not in MAY_READ_TRUTH:
            assert '"truth"' not in text and "'truth'" not in text, path.name


def test_the_workbench_never_imports_the_simulator() -> None:
    for path in SRC.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("rdw_sim"), path.name
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("rdw_sim") for a in node.names), path.name
