from pathlib import Path


CONTRACT = Path("docs/browser-route-contract.md")


def contract_text():
    return CONTRACT.read_text(encoding="utf-8")


def test_contract_declares_exact_route_sequence():
    text = contract_text()
    assert "Playwright → screenshot + visão nativa → image-analyzer → stop" in text


def test_contract_names_normative_routes_and_safe_stop():
    text = contract_text()
    for phrase in (
        "playwright",
        "screenshot+nativa",
        "image-analyzer",
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


def test_contract_persists_timestamp_only_after_scheduled_list_confirmation():
    text = contract_text()
    persistence_index = text.index("persistência local")
    scheduled_list_index = text.index("scheduled_list_confirmed")
    timestamp_registered_index = text.index("timestamp_registered")
    assert scheduled_list_index < timestamp_registered_index < persistence_index


def test_contract_rejects_new_composer_and_duplicate_mutation():
    text = contract_text()
    mutation_section = text[text.index("## Publicar") : text.index("## Registro mínimo")]
    assert "nunca abrir novo composer" in mutation_section
    assert "não criar uma duplicata" in mutation_section


def test_contract_separates_read_and_mutation_rules():
    text = contract_text()
    read_section = text[text.index("## Leitura e inspeção") : text.index("## Publicar")]
    mutation_section = text[text.index("## Publicar") : text.index("## Registro mínimo")]
    assert "playwright" in read_section
    assert "screenshot+nativa" in read_section
    assert "image-analyzer" in read_section
    assert "confirmar o alvo" in mutation_section
    assert "após o envio, verificar o estado" in mutation_section
