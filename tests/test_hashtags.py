"""Testes do gerador de hashtags (hashtags.py).

As hashtags são derivadas dos sinais indicadores do topic: pilares,
mecanismo central e veredito de novidade. Regra: 3 a 5 por draft.
"""

import pytest

from hashtags import (
    MAX_HASHTAGS,
    MIN_HASHTAGS,
    _slug,
    generate_hashtags,
    hashtags_for_topic,
    load_topics,
)

SIGNALS = {
    "signal_1": {
        "id": "signal_1",
        "title": "Prova de entrega que aceita qualquer dado não é controle",
        "observation": "Nome e telefone errados ainda marcam o pedido como entregue.",
        "possible_angle": "Controle que aceita qualquer entrada é teatro de conformidade.",
    },
    "signal_2": {
        "id": "signal_2",
        "title": "Mentira no status de entrega custa mais que a falha admitida",
        "observation": "Marcar como entregue remove o recurso do cliente.",
        "possible_angle": "A integridade do status é o controle.",
    },
}


def _topic(**overrides):
    topic = {
        "id": "topic_x",
        "title": "Prova de entrega que aceita qualquer dado não é controle",
        "possible_thesis": "Controle que aceita qualquer entrada não é controle.",
        "central_question": "O que separa uma prova de entrega real de um carimbo?",
        "pillars": ["logistica_last_mile_cx"],
        "signals": ["signal_1", "signal_2"],
        "novelty": {"verdict": "new"},
    }
    topic.update(overrides)
    return topic


# --- slug -----------------------------------------------------------------


def test_slug_removes_accents_and_uses_pascal_case():
    assert _slug("última milha") == "UltimaMilha"
    assert _slug("governança de IA") == "GovernancaDeIA"


# --- geração --------------------------------------------------------------


def test_generates_between_min_and_max():
    tags = generate_hashtags(_topic(), SIGNALS)
    assert MIN_HASHTAGS <= len(tags) <= MAX_HASHTAGS


def test_hashtags_are_prefixed_and_unique():
    tags = generate_hashtags(_topic(), SIGNALS)
    rendered = [t["tag"] for t in tags]
    assert all(t.startswith("#") for t in rendered)
    assert len(rendered) == len(set(rendered))


def test_each_hashtag_has_origin_and_reason():
    for item in generate_hashtags(_topic(), SIGNALS):
        assert item["origin"]
        assert item["reason"]


def test_mechanism_from_core_is_used():
    tags = {t["tag"] for t in generate_hashtags(_topic(), SIGNALS)}
    assert "#ProvaDeEntrega" in tags


def test_pillar_tags_are_used():
    tags = {t["tag"] for t in generate_hashtags(_topic(), SIGNALS)}
    assert "#UltimaMilha" in tags


def test_revisited_topic_gets_angle_tag():
    topic = _topic(novelty={"verdict": "revisited", "vs_published": ["topic_old"], "delta": "x" * 80})
    tags = {t["tag"] for t in generate_hashtags(topic, SIGNALS)}
    assert "#AnguloNovo" in tags


def test_new_topic_does_not_get_angle_tag():
    tags = {t["tag"] for t in generate_hashtags(_topic(), SIGNALS)}
    assert "#AnguloNovo" not in tags


def test_generic_word_alone_does_not_create_tag():
    """'custo' solto num sinal não deve virar hashtag de custo."""
    topic = _topic(
        title="Accountability só funciona com autoridade",
        possible_thesis="Cobrança sem autoridade é só pressão.",
        central_question="O que faz a cobrança pegar?",
        pillars=["lideranca_operacoes"],
        signals=[],
    )
    tags = {t["tag"] for t in generate_hashtags(topic, {})}
    assert "#CustoOperacional" not in tags


def test_fallback_derives_from_title_when_few_signals():
    topic = _topic(
        title="Rastreabilidade de cacau vira rede de identidade",
        possible_thesis="Rastreabilidade sustenta prova e resposta.",
        central_question="Como provar origem?",
        pillars=[],
        signals=[],
        novelty={"verdict": "new"},
    )
    tags = generate_hashtags(topic, {})
    assert len(tags) >= MIN_HASHTAGS


def test_never_exceeds_max():
    topic = _topic(
        title="Agentes de IA em produção com observabilidade e permissões e custo",
        possible_thesis="Governança de IA, regulação, segurança e qualidade de dado.",
        central_question="Como avaliar o agente em produção?",
        pillars=["ia_aplicada", "riscos_compliance_resiliencia"],
        signals=["signal_1", "signal_2"],
        novelty={"verdict": "revisited", "vs_published": ["topic_old"], "delta": "x" * 80},
    )
    assert len(generate_hashtags(topic, SIGNALS)) <= MAX_HASHTAGS


# --- integração com os topics reais ---------------------------------------


def test_real_topics_have_three_to_five_hashtags():
    topics = load_topics()
    assert topics, "nenhum topic encontrado"
    for topic_id in topics:
        tags = hashtags_for_topic(topic_id)
        assert MIN_HASHTAGS <= len(tags) <= MAX_HASHTAGS, topic_id


def test_unknown_topic_raises():
    with pytest.raises(KeyError):
        hashtags_for_topic("topic_inexistente_999")
