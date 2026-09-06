from pathlib import Path


CONTRACT = Path("docs/browser-route-contract.md")


def contract_text():
    return CONTRACT.read_text(encoding="utf-8")


def test_contract_declares_exact_route_sequence():
    text = contract_text()
    assert "MCP Chrome DevTools → Playwright (fallback) → stop" in text


def test_contract_names_normative_routes_and_safe_stop():
    text = contract_text()
    for phrase in (
        "mcp_chrome_devtools",
        "playwright_fallback",
        "ambiguous_mutation",
        "fail-closed",
        "nunca abrir novo composer",
    ):
        assert phrase in text


def test_fallback_is_allowed_only_before_confirmed_mutation():
    text = contract_text()
    assert "somente antes de uma mutação ser confirmada" in text
    assert "fallback não é permitido" in text
    assert "repetir" in text and "a ação" in text


def test_ambiguous_mutation_requires_state_verification_and_fail_closed():
    text = contract_text()
    assert "ambiguous_mutation" in text
    assert "verificar o estado resultante" in text
    assert "aplicar `fail_closed`" in text


def test_contract_requires_effective_route_and_state_records():
    text = contract_text()
    assert "rota efetiva" in text
    assert "verificação do estado" in text


def test_contract_separates_read_and_mutation_rules():
    text = contract_text()
    read_section = text[text.index("## Leitura e inspeção") : text.index("## Publicar")]
    mutation_section = text[text.index("## Publicar") : text.index("## Registro mínimo")]
    assert "mcp_chrome_devtools" in read_section
    assert "playwright_fallback" in read_section
    assert "confirmar o alvo" in mutation_section
    assert "após o envio, verificar o estado" in mutation_section
