"""Testes do gerador de hashtags (hashtags.py).

As hashtags são **trazidas pelas fontes**: cada sinal carrega
`source.source_hashtags`. O gerador prioriza essas hashtags reais e só
recorre a vocabulário derivado do tema quando a fonte não trouxe nenhuma.
Regra: 3 a 5 por draft.
"""

import pytest

from hashtags import (
    MAX_HASHTAGS,
    MIN_HASHTAGS,
    _normalize_tag,
    _slug,
    fallback_hashtags,
    generate_hashtags,
    hashtags_for_topic,
    load_topics,
    source_hashtags,
)

SIGNALS = {
    "signal_1": {
        "id": "signal_1",
        "title": "Prova de entrega que aceita qualquer dado não é controle",
        "observation": "Nome e telefone errados ainda marcam o pedido como entregue.",
        "source": {"source_hashtags": ["#LastMile", "#SupplyChain", "#Delivery"]},
    },
    "signal_2": {
        "id": "signal_2",
        "title": "Mentira no status de entrega custa mais que a falha admitida",
        "observation": "Marcar como entregue remove o recurso do cliente.",
        "source": {"source_hashtags": ["#LastMile", "#OrderAccuracy"]},
    },
}

SIGNALS_NO_TAGS = {
    "signal_3": {
        "id": "signal_3",
        "title": "Agente em produção",
        "observation": "Observabilidade e qualidade de dado.",
        "source": {},
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


# --- slug e normalização --------------------------------------------------


def test_slug_removes_accents_and_uses_pascal_case():
    assert _slug("última milha") == "UltimaMilha"
    assert _slug("governança de IA") == "GovernancaDeIA"


def test_normalize_tag_keeps_hash_and_pascal_case():
    assert _normalize_tag("#lastmile") == "#Lastmile"
    assert _normalize_tag("#SupplyChain") == "#SupplyChain"


# --- hashtags das fontes --------------------------------------------------


def test_source_hashtags_are_used_first():
    tags = [t["tag"] for t in source_hashtags(_topic(), SIGNALS)]
    assert "#LastMile" in tags
    assert "#SupplyChain" in tags


def test_source_hashtags_ranked_by_frequency():
    """#LastMile aparece em 2 sinais, deve vir antes das de 1."""
    tags = [t["tag"] for t in source_hashtags(_topic(), SIGNALS)]
    assert tags[0] == "#LastMile"


def test_source_hashtags_have_origin_and_reason():
    for item in source_hashtags(_topic(), SIGNALS):
        assert item["origin"] == "fonte"
        assert "sinal" in item["reason"]


def test_platform_noise_is_filtered():
    signals = {
        "s": {
            "id": "s",
            "source": {"source_hashtags": ["#fyp", "#viral", "#LastMile", "#TechTok"]},
        }
    }
    tags = [t["tag"] for t in source_hashtags(_topic(signals=["s"]), signals)]
    assert tags == ["#LastMile"]


def test_identity_noise_is_filtered():
    signals = {
        "s": {
            "id": "s",
            "source": {"source_hashtags": ["#COO", "#Founders", "#Leadership"]},
        }
    }
    tags = [t["tag"] for t in source_hashtags(_topic(signals=["s"]), signals)]
    assert tags == ["#Leadership"]


def test_truncated_tag_is_removed_when_longer_variant_exists():
    signals = {
        "s": {
            "id": "s",
            "source": {"source_hashtags": ["#Accounta", "#Accountability"]},
        }
    }
    tags = [t["tag"] for t in source_hashtags(_topic(signals=["s"]), signals)]
    assert tags == ["#Accountability"]


# --- fallback -------------------------------------------------------------


def test_fallback_used_when_source_has_no_tags():
    tags = generate_hashtags(_topic(signals=["signal_3"]), SIGNALS_NO_TAGS)
    assert MIN_HASHTAGS <= len(tags) <= MAX_HASHTAGS
    assert all(t["origin"] != "fonte" for t in tags)


def test_fallback_mechanism_from_core():
    tags = {t["tag"] for t in fallback_hashtags(_topic(), SIGNALS)}
    assert "#ProvaDeEntrega" in tags


def test_fallback_pillar_tags():
    tags = {t["tag"] for t in fallback_hashtags(_topic(), SIGNALS)}
    assert "#UltimaMilha" in tags


# --- geração combinada ----------------------------------------------------


def test_generates_between_min_and_max():
    tags = generate_hashtags(_topic(), SIGNALS)
    assert MIN_HASHTAGS <= len(tags) <= MAX_HASHTAGS


def test_hashtags_are_prefixed_and_unique():
    rendered = [t["tag"] for t in generate_hashtags(_topic(), SIGNALS)]
    assert all(t.startswith("#") for t in rendered)
    assert len(rendered) == len(set(rendered))


def test_source_tags_take_priority_over_fallback():
    """Com 3+ hashtags de fonte, o fallback não entra."""
    tags = generate_hashtags(_topic(), SIGNALS)
    assert all(t["origin"] == "fonte" for t in tags)


def test_fallback_completes_when_source_has_few_tags():
    signals = {
        "s": {"id": "s", "source": {"source_hashtags": ["#LastMile"]}},
    }
    tags = generate_hashtags(_topic(signals=["s"]), signals)
    assert len(tags) >= MIN_HASHTAGS
    assert tags[0]["origin"] == "fonte"
    assert any(t["origin"] != "fonte" for t in tags)


def test_never_exceeds_max():
    signals = {
        "s": {
            "id": "s",
            "source": {
                "source_hashtags": [
                    "#A", "#B", "#C", "#D", "#E", "#F", "#G", "#H",
                ]
            },
        }
    }
    assert len(generate_hashtags(_topic(signals=["s"]), signals)) <= MAX_HASHTAGS


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
