from pathlib import Path


FILES = (
    Path(".agents/skills/publicar-linkedin/SKILL.md"),
    Path("README.md"),
    Path("mapa.md"),
    Path("docs/superpowers/plans/2026-09-01-linkedin-scheduling.md"),
    Path("docs/superpowers/specs/2026-09-01-editorial-batch-gauntlet-design.md"),
    Path("docs/roadmap.md"),
)


def test_browser_docs_use_mcp_before_playwright():
    for path in FILES:
        text = path.read_text()
        assert "MCP Chrome DevTools" in text, path
        assert text.index("MCP Chrome DevTools") < text.index("Playwright"), path
        assert "playwright_fallback" in text or "fallback" in text.lower(), path


def test_docs_retain_critical_linkedin_safety_rules():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "Alterar agenda" in text
    assert "Publicações agendadas" in text
    assert "novo composer" in text
