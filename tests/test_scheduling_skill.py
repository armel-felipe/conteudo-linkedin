from pathlib import Path


SKILL = Path(".agents/skills/publicar-linkedin/SKILL.md")


def read_skill():
    return SKILL.read_text()


def test_native_vision_route_is_ordered_and_has_explicit_failure_reasons():
    text = read_skill()
    assert "Playwright → screenshot + visão nativa → image-analyzer(native_failed) → stop" in text

    no_native = text[text.index("## Visão e rota de interação") :]
    assert "não tiver visão nativa" in no_native
    assert "reason: no_native_vision" in no_native
    assert "sem tentar visão nativa" in no_native

    native_failed = no_native.index("reason: native_failed")
    stop = no_native.index("parar, relatar a limitação", native_failed)
    assert native_failed < stop


def test_scheduling_has_visual_gates_before_advancing_and_agending():
    text = read_skill()
    scheduling = text[text.index("## Agendamento — detalhes") :]

    assert 'resumo visual antes de "Avançar"' in scheduling
    assert 'prévia final antes de "Agendar"' in scheduling
    assert text.index("6. Verificar o agendamento") < text.index("7. Somente depois da verificação")


def test_approved_text_needs_no_new_textual_approval_but_needs_visual_validation():
    text = read_skill()

    assert "NÃO pedir nova confirmação textual" in text
    assert 'validação visual do resumo, da prévia final e da publicação em "Publicações agendadas" é obrigatória' in text
    assert "sem pausa na skill e sem nova validação" not in text


def test_existing_scheduled_post_is_changed_in_place_without_duplicate():
    text = read_skill()
    reschedule = text[text.index("### Reagendamento") : text.index("## Registro do agendamento")]

    assert "publicação existente" in reschedule
    assert "... → Alterar agenda" in reschedule
    assert "Nunca criar duplicata" in reschedule
    assert "Não abrir um compositor novo" not in reschedule
    assert "nem abrir um compositor novo" in reschedule
