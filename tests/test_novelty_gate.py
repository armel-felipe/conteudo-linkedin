"""Testes do gate de novidade editorial (novelty_gate.py).

O gate é fail-closed: um topic sem `novelty` válido não é elegível para o
Bloco 2, mesmo com `status: ready_for_research`.
"""

import textwrap

import pytest
import yaml

from editorial_batch import load_and_select_topics
from novelty_gate import (
    detect_overlap,
    is_eligible,
    load_published_topics,
    validate_novelty,
)

PUBLISHED = {
    "topic_20260914_08": {
        "id": "topic_20260914_08",
        "title": "Quando a operação falha, a ausência de humano transforma atraso em crise",
        "possible_thesis": (
            "O cliente não perdoa a falha, perdoa a demora — mas não perdoa ficar "
            "preso no loop: quando a operação quebra e não existe humano alcançável, "
            "o atraso vira crise de confiança."
        ),
        "central_question": "Quando o cliente precisa de um humano, ele encontra um?",
        "status": "published",
    },
    "topic_20260915_03": {
        "id": "topic_20260915_03",
        "title": "Na última milha, a promessa cumprida vale mais que a velocidade",
        "possible_thesis": (
            "A última milha madura não mede apenas velocidade ou entrega no prazo; "
            "mede a promessa percebida, o custo da operação e a velocidade de "
            "recuperação quando o plano quebra."
        ),
        "central_question": "Qual indicador revela a qualidade real da última milha?",
        "status": "published",
    },
}


def _topic(**overrides):
    topic = {
        "id": "topic_20260923_99",
        "title": "Tema novo",
        "possible_thesis": "Uma tese qualquer sobre operação.",
        "central_question": "Pergunta?",
        "status": "candidate",
    }
    topic.update(overrides)
    return topic


# --- camada 2: validação do campo novelty ---------------------------------


def test_missing_novelty_is_blocked():
    problems = validate_novelty(_topic(), PUBLISHED)
    assert problems
    assert not is_eligible(_topic(), PUBLISHED)


def test_invalid_verdict_is_blocked():
    topic = _topic(novelty={"verdict": "talvez"})
    assert validate_novelty(topic, PUBLISHED)


def test_new_verdict_without_vs_published_is_eligible():
    topic = _topic(novelty={"verdict": "new"})
    assert validate_novelty(topic, PUBLISHED) == []
    assert is_eligible(topic, PUBLISHED)


def test_new_verdict_cannot_declare_vs_published():
    topic = _topic(novelty={"verdict": "new", "vs_published": ["topic_20260914_08"]})
    assert validate_novelty(topic, PUBLISHED)


def test_duplicate_verdict_is_blocked():
    topic = _topic(novelty={"verdict": "duplicate"})
    problems = validate_novelty(topic, PUBLISHED)
    assert problems
    assert not is_eligible(topic, PUBLISHED)


def test_revisited_requires_vs_published_and_delta():
    assert validate_novelty(_topic(novelty={"verdict": "revisited"}), PUBLISHED)
    assert validate_novelty(
        _topic(novelty={"verdict": "revisited", "vs_published": ["topic_20260914_08"]}),
        PUBLISHED,
    )


def test_revisited_with_substantive_delta_is_eligible():
    topic = _topic(
        novelty={
            "verdict": "revisited",
            "vs_published": ["topic_20260914_08"],
            "delta": (
                "O post anterior tratou da ausência de humano na falha. Este trata "
                "do mecanismo de falsificação do status de entrega: um controle que "
                "aceita qualquer entrada e por isso não prova nada."
            ),
            "new_case": "Issue do GitHub documentando que nome e telefone errados "
            "ainda retornam sucesso e marcam o pedido como entregue.",
        }
    )
    assert validate_novelty(topic, PUBLISHED) == []
    assert is_eligible(topic, PUBLISHED)


def test_revisited_with_short_delta_is_blocked():
    topic = _topic(
        novelty={
            "verdict": "revisited",
            "vs_published": ["topic_20260914_08"],
            "delta": "É diferente.",
        }
    )
    assert validate_novelty(topic, PUBLISHED)


def test_revisited_with_rewritten_thesis_is_blocked():
    """Delta que só reescreve a tese anterior não se sustenta."""
    topic = _topic(
        novelty={
            "verdict": "revisited",
            "vs_published": ["topic_20260914_08"],
            "delta": (
                "O cliente não perdoa a falha, perdoa a demora, mas não perdoa ficar "
                "preso no loop quando a operação quebra e não existe humano alcançável, "
                "e o atraso vira crise de confiança."
            ),
        }
    )
    assert validate_novelty(topic, PUBLISHED)


def test_unknown_vs_published_is_blocked():
    topic = _topic(
        novelty={
            "verdict": "revisited",
            "vs_published": ["topic_20990101_99"],
            "delta": "Um delta suficientemente longo para passar do tamanho mínimo exigido.",
        }
    )
    assert validate_novelty(topic, PUBLISHED)


# --- camada 1: detecção de sobreposição -----------------------------------


def test_detect_overlap_ranks_similar_topic_first():
    topic = _topic(
        title="Prova de entrega que aceita qualquer dado não é controle",
        possible_thesis=(
            "Controle que aceita qualquer entrada não é controle: é teatro de "
            "conformidade, e a mentira no status de entrega custa mais ao cliente "
            "do que a falha admitida."
        ),
        central_question="O que separa uma prova de entrega real de um carimbo?",
    )
    ranked = detect_overlap(topic, PUBLISHED)
    assert ranked
    assert ranked[0][1] == "topic_20260914_08"


def test_detect_overlap_returns_empty_for_unrelated_topic():
    topic = _topic(
        title="Enforcement do EU AI Act desce a cadeia de fornecedores",
        possible_thesis="A obrigação de transparência segue o cliente, não o CNPJ.",
        central_question="O que muda quando a regra passa a ser exigível?",
    )
    ranked = detect_overlap(topic, PUBLISHED)
    assert all(score < 0.30 for score, _ in ranked)


# --- integração: load_published_topics e o lote ---------------------------


def test_load_published_topics_reads_published_and_archived(tmp_path):
    (tmp_path / "topics_2026-09-14.yaml").write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {"id": "topic_a", "status": "published", "title": "A"},
                    {"id": "topic_b", "status": "archived", "title": "B"},
                    {"id": "topic_c", "status": "candidate", "title": "C"},
                ]
            }
        ),
        encoding="utf-8",
    )
    published = load_published_topics(tmp_path)
    assert set(published) == {"topic_a", "topic_b"}


def test_batch_blocks_topic_without_novelty(tmp_path):
    (tmp_path / "topics_2026-09-23.yaml").write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "topic_20260923_01",
                        "title": "Sem novelty",
                        "status": "ready_for_research",
                        "scores": {"total": 90.0},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## 90 — Sem novelty\n\ntopic_20260923_01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="gate de novidade"):
        load_and_select_topics(backlog, tmp_path, "all")


def test_batch_allows_topic_with_valid_novelty(tmp_path):
    (tmp_path / "topics_2026-09-23.yaml").write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "topic_20260923_01",
                        "title": "Com novelty",
                        "status": "ready_for_research",
                        "scores": {"total": 90.0},
                        "novelty": {"verdict": "new"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## 90 — Com novelty\n\ntopic_20260923_01\n", encoding="utf-8")

    selected = load_and_select_topics(backlog, tmp_path, "all")
    assert [t["topic_id"] for t in selected] == ["topic_20260923_01"]


def test_batch_explicit_selection_reports_novelty_block(tmp_path):
    (tmp_path / "topics_2026-09-23.yaml").write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {
                        "id": "topic_20260923_01",
                        "title": "Duplicado",
                        "status": "ready_for_research",
                        "scores": {"total": 90.0},
                        "novelty": {"verdict": "duplicate"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## 90 — Duplicado\n\ntopic_20260923_01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_and_select_topics(backlog, tmp_path, "topic_20260923_01")
