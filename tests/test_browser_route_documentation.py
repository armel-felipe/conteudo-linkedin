from pathlib import Path
import re
import yaml


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
        mcp = text.index("MCP Chrome DevTools")
        playwright = text.index("Playwright", mcp)
        screenshot = text.lower().index("screenshot", playwright)
        stop = text.lower().index("stop", screenshot)

        assert mcp < playwright < screenshot < stop, path
        assert "playwright_fallback" in text, path
        assert "registr" in text.lower(), path
        assert "motivo" in text.lower() or "raz" in text.lower(), path
        assert "fail-closed" in text.lower(), path
        assert not re.search(
            r"(?:primeir[ao]\s+(?:tentativa|rota)|tentar\s+primeiro)\D{0,30}Playwright|"
            r"Playwright\s+(?:é|e)\s+(?:a\s+)?(?:primeira|rota\s+inicial)",
            text,
            re.IGNORECASE,
        ), path


def test_visual_fallback_is_not_a_control_route():
    for path in FILES:
        text = path.read_text().lower()
        assert "depois" in text and "duas rotas" in text or "pós-rotas" in text, path
        assert "evidência" in text or "evidencia" in text, path


def test_editorial_batch_cannot_publish_or_schedule():
    text = "\n".join(path.read_text() for path in FILES)
    assert "run-editorial-batch" in text
    assert re.search(r"lote.{0,120}não publica", text, re.IGNORECASE | re.DOTALL)
    assert re.search(r"lote.{0,120}não.*agenda", text, re.IGNORECASE | re.DOTALL)


def test_roadmap_receipt_uses_canonical_route_identifiers():
    text = Path("docs/roadmap.md").read_text()
    receipt_text = text.split("### Receipt estruturada", 1)[1].split("```yaml\n", 1)[1].split("\n```", 1)[0]
    receipt = yaml.safe_load(receipt_text)
    assert receipt["route"] == "stop"
    assert receipt["fallback"] == "none"
    assert receipt["route_attempted"] == ["mcp_chrome_devtools"]
    assert receipt["mcp_attempted"] is True
    assert receipt["route_reasons"]["mcp_chrome_devtools"]
    assert receipt["observed_state"]
    assert receipt["verification_evidence"]
    assert receipt["post_action_confirmation"] == "not_run"
    assert "route: browser_cdp" not in text
    assert "fallback: native" not in text
    assert "real_existing_post: confirmado" not in text


def test_docs_retain_critical_linkedin_safety_rules():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "Alterar agenda" in text
    assert "Publicações agendadas" in text
    assert "novo composer" in text


def test_linkedin_skill_uses_canonical_browser_events():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "mcp_chrome_devtools_attempt" in text
    assert "playwright_fallback" in text
    assert "playwright_attempt" in text
    assert "playwright_fallback_if_needed" not in text


def test_mutation_docs_define_fail_closed_boundary_as_behavior():
    text = Path("docs/browser-route-contract.md").read_text(encoding="utf-8")
    mutation_section = text[text.index("## Publicar") : text.index("## Registro mínimo")]
    assert "ambiguous_mutation" in mutation_section
    assert "não repetir" in mutation_section
    assert "não avançar" in mutation_section
    assert "não criar uma duplicata" in mutation_section
    assert mutation_section.index("após o envio") < mutation_section.index("ambiguous_mutation")


def test_docs_make_timestamp_gate_exclude_non_mutating_evidence():
    text = Path("docs/browser-route-contract.md").read_text(encoding="utf-8")
    assert "Somente evidência `real_existing_post`" in text
    assert "`real_non_destructive`, `simulated` e `not_run`" in text
    assert "devem ser rejeitados pelo gate" in text
