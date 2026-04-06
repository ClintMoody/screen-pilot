import asyncio

from screen_pilot.server import create_mcp_server


def test_mcp_server_has_all_tools():
    server = create_mcp_server()
    tools = asyncio.run(server.list_tools())
    tool_names = [t.name for t in tools]
    expected = [
        "screenshot", "click", "type_text", "press_key",
        "scroll", "drag", "hover", "wait",
        "detect_ui_elements", "desktop_task",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_mcp_server_tool_count():
    server = create_mcp_server()
    tools = asyncio.run(server.list_tools())
    assert len(tools) == 10
