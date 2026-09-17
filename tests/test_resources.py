"""Verify the UI resource registration and generated bundle contract.

Add assertions here when changing resource metadata or frontend build output.
"""

import pytest
from fastmcp import FastMCP

from app.ui.frappe_ui.resource import VIEW_PATH, VIEW_URI, register_resource


@pytest.mark.asyncio
async def test_frappe_ui_resource_is_registered_and_bundled():
    assert VIEW_PATH.is_file(), "Build the UI before running the complete test suite"

    mcp = FastMCP("test-server")
    register_resource(mcp)

    resource = await mcp.get_resource(VIEW_URI)
    html = await resource.read()

    assert "Frappe" in html
    assert "twynity-frappe-dashboard" in html
    assert ".render(React.createElement" not in html
