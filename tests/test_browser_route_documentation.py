from pathlib import Path

FILES = (
    Path(".agents/skills/publicar-linkedin/SKILL.md"),
    Path("README.md"),
    Path("mapa.md"),
    Path("docs/browser-route-contract.md"),
)

ROUTE_FILES = (
    Path(".agents/skills/publicar-linkedin/SKILL.md"),
    Path("docs/browser-route-contract.md"),
)


def test_current_browser_docs_use_visual_route_before_playwright():
    for path in FILES:
        text = path.read_text()
        assert "browser_native" in text, path
        visual = min(text.index("browser_native"), text.index("screenshot/AX"))
        playwright = text.find("Playwright", visual)
        stop = text.lower().find("stop", playwright)

        assert visual < playwright < stop, path
        assert "image-analyzer" in text, path
        assert "registr" in text.lower(), path
        assert "motivo" in text.lower() or "raz" in text.lower(), path
        assert "fail-closed" in text.lower(), path


def test_route_files_name_real_embedded_browser():
    for path in ROUTE_FILES:
        text = path.read_text()
        assert "CUA embedded browser" in text, path
        assert "Playwright read-only" in text, path


def test_visual_fallback_is_not_a_control_route():
    for path in FILES:
        text = path.read_text().lower()
        assert "primeira" in text or "obrigat" in text, path
        assert "evidência" in text or "evidencia" in text, path


def test_editorial_batch_cannot_publish_or_schedule():
    text = "\n".join(path.read_text() for path in FILES)
    assert "run-editorial-batch" in text
    assert "não publica" in text
    assert "não" in text
    assert "agenda" in text


def test_active_roadmap_records_completed_scheduling_plan_without_checklist_noise():
    text = Path("docs/roadmap.md").read_text()
    assert "scheduling-restart" in text
    assert "Nenhuma" in text
    assert "executado e encerrado" in text
    assert "- [x]" not in text
    assert "- [~]" not in text
    assert "- [!]" not in text
    assert "Receipt estruturada" not in text


def test_docs_retain_critical_linkedin_safety_rules():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "Alterar agenda" in text
    assert "Publicações agendadas" in text
    assert "novo composer" in text


def test_linkedin_skill_uses_visual_first_browser_events():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "browser_attempt" in text
    assert "screenshot" in text
    assert "visual_route" in text
    assert "playwright_attempt" in text
    assert "mcp_chrome_devtools_attempt" not in text


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
