"""ironmcp conformance: every zhcorpus tool enforces advertisement == runtime.

Uses the SYNC wrapper (zhcorpus tests are synchronous; no asyncio_mode configured).
"""
from ironmcp import assert_enforces_v2

from zhcorpus.mcp.server import mcp


def test_all_tools_enforce_closed_contract():
    enforced = assert_enforces_v2(mcp)
    assert enforced >= 6, f"expected ~8 tools to enforce advertise==runtime, got {enforced}"
