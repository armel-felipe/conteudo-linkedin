from pathlib import Path


def test_browser_route_contract_declares_mcp_first_and_safe_fallback():
    text = Path("docs/browser-route-contract.md").read_text()
    assert text.index("MCP Chrome DevTools") < text.index("Playwright")
    for phrase in (
        "mcp_chrome_devtools",
        "playwright_fallback",
        "ambiguous_mutation",
        "fail-closed",
        "nunca abrir novo composer",
    ):
        assert phrase in text
