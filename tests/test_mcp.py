from __future__ import annotations

import asyncio


def test_the_strategist_tools_are_exposed() -> None:
    from rdw.mcp_server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"customer_brief", "readiness", "value_case", "steerco_pack", "platform_signals", "record_decision"} <= names
