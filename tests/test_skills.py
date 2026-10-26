"""The skills in skills/ are the context layer for strategists using Claude: they must call tools that exist."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import yaml

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def _skills() -> list[Path]:
    return sorted(SKILLS.glob("*/SKILL.md"))


def test_every_skill_has_frontmatter_with_a_name_matching_its_folder() -> None:
    assert len(_skills()) >= 4
    for path in _skills():
        text = path.read_text(encoding="utf-8")
        front = yaml.safe_load(text.split("---")[1])
        assert front["name"] == path.parent.name
        assert 20 < len(front["description"]) <= 1024


def test_skills_only_call_tools_the_mcp_server_has() -> None:
    from rdw.mcp_server import mcp

    tools = {t.name for t in asyncio.run(mcp.list_tools())}
    for path in _skills():
        called = set(re.findall(r"`([a-z_]+)\(", path.read_text(encoding="utf-8")))
        assert called, path
        assert called <= tools, (path.name, called - tools)
