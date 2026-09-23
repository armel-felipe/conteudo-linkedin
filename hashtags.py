#!/usr/bin/env python3
"""hashtags.py — Gera hashtags para um draft a partir dos sinais do topic.

As hashtags são derivadas dos **sinais indicadores** do topic: pilares,
fenômeno central, mecanismo operacional e veredito de novidade. Não são
genéricas nem de volume — cada uma precisa ser rastreável a um sinal real.

Uso:
  # Hashtags para um topic
  python hashtags.py topic_20260923_07

  # Com justificativa por hashtag
  python hashtags.py topic_20260923_07 --explain

  # A partir de um draft (lê o topic_id do nome do arquivo)
  python hashtags.py --draft content/drafts/topic_20260923_07.md
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
TOPICS_DIR = ROOT / "research" / "topics"
SIGNALS_DIR = ROOT / "research" / "signals"

MIN_HASHTAGS = 3
MAX_HASHTAGS = 5

# Vocabulário por pilar: hashtags ancoradas no domínio do tema.
PILLAR_TAGS = {
    "ia_aplicada": ["IAAplicada", "AgentesDeIA", "IAEmProducao"],
    "logistica_last_mile_cx": ["UltimaMilha", "Logistica", "ExperienciaDoCliente"],
    "lideranca_operacoes": ["LiderancaOperacional", "Accountability", "GestaoDeTimes"],
    "riscos_compliance_resiliencia": ["GovernancaDeIA", "Compliance", "ResilienciaOperacional"],
    "alimentos_consumo_sustentabilidade": ["CadeiaAlimentar", "Sustentabilidade", "Desperdicio"],
}

# Vocabulário por mecanismo detectado no texto do topic.
# Cada padrão precisa ser específico: termos genéricos ("custo", "dado")
# só contam quando aparecem em contexto que os torna o mecanismo do tema.
MECHANISM_TAGS = {
    r"prova de entrega|proof of delivery|status de entrega|marcad[oa] como entregue": "ProvaDeEntrega",
    r"custo (da|por|unitári|operacion)|margem|economia unit|53%": "CustoOperacional",
    r"confiabil|promessa cumprida|previsibilidade|no prazo": "ConfiabilidadeDeEntrega",
    r"permiss|autoriza|identidade do agente|just-in-time": "PermissoesDeAgente",
    r"observab|tracing|monitorar o agente|visibilidade": "Observabilidade",
    r"avalia(r|ção) (do|de) agente|eval|benchmark|régua": "AvaliacaoDeAgente",
    r"ai act|regula(ção|r) de ia|enforcement|omnibus": "RegulacaoDeIA",
    r"prompt injection|exploit|capacidade ofensiva|ataque": "SegurancaDeIA",
    r"qualidade de dado|dado confiável|rastreabilidade|dado em tempo real": "QualidadeDeDados",
    r"handoff|passagem de bastão|delega(r|ção)": "DelegacaoEHandoff",
    r"accountab|cobrança|consequência para o descumprimento": "Accountability",
    r"desperdício|resíduo|food waste|shelf-life": "DesperdicioAlimentar",
    r"recall|segurança alimentar|food safety": "SegurancaAlimentar",
    r"agente de ia|agentes de ia|ai agent|agente autônomo": "AgentesDeIA",
    r"em produção|produção real|depois do deploy|além da demo": "IAEmProducao",
}


def _slug(text: str) -> str:
    """PascalCase sem acento, para uso como hashtag."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[A-Za-z0-9]+", ascii_text)
    return "".join(w[:1].upper() + w[1:] for w in words)


def load_topics(topics_dir: Path | None = None) -> dict[str, dict]:
    directory = topics_dir or TOPICS_DIR
    topics: dict[str, dict] = {}
    for path in sorted(directory.glob("topics_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for topic in document.get("topics", []):
            topic_id = topic.get("id") or topic.get("topic_id")
            if topic_id:
                topics[topic_id] = topic
    return topics


def load_signals(signals_dir: Path | None = None) -> dict[str, dict]:
    directory = signals_dir or SIGNALS_DIR
    signals: dict[str, dict] = {}
    for path in sorted(directory.glob("signals_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for signal in document.get("signals", []):
            if signal.get("id"):
                signals[signal["id"]] = signal
    return signals


def _topic_text(topic: dict, signals: dict[str, dict]) -> str:
    parts = [
        str(topic.get("title", "")),
        str(topic.get("possible_thesis", "")),
        str(topic.get("central_question", "")),
    ]
    for signal_id in topic.get("signals") or []:
        signal = signals.get(signal_id)
        if not signal:
            continue
        parts.append(str(signal.get("title", "")))
        parts.append(str(signal.get("observation", "")))
    return " ".join(parts).lower()


def _core_text(topic: dict) -> str:
    """Núcleo do tema: título, tese e pergunta. Onde o mecanismo é central."""
    return " ".join(
        str(topic.get(field, ""))
        for field in ("title", "possible_thesis", "central_question")
    ).lower()


def generate_hashtags(topic: dict, signals: dict[str, dict]) -> list[dict]:
    """Hashtags com justificativa, ordenadas por força do sinal.

    Um mecanismo só vira hashtag quando aparece no **núcleo** do tema
    (título, tese ou pergunta) ou em pelo menos dois sinais. Isso evita
    hashtags de ruído — palavras comuns como "custo" que aparecem em
    qualquer texto não viram tag.

    Retorna lista de {tag, origin, reason}. Entre 3 e 5 itens.
    """
    core = _core_text(topic)
    full = _topic_text(topic, signals)
    candidates: list[dict] = []
    seen: set[str] = set()

    def add(tag: str, origin: str, reason: str) -> None:
        if tag in seen:
            return
        seen.add(tag)
        candidates.append({"tag": f"#{tag}", "origin": origin, "reason": reason})

    # 1. Mecanismos no núcleo do tema (mais forte).
    for pattern, tag in MECHANISM_TAGS.items():
        if re.search(pattern, core):
            add(tag, "mecanismo (núcleo)", f"presente no título/tese: /{pattern}/")

    # 2. Mecanismos recorrentes nos sinais (aparecem em 2+ sinais).
    for pattern, tag in MECHANISM_TAGS.items():
        if tag in seen:
            continue
        hits = 0
        for signal_id in topic.get("signals") or []:
            signal = signals.get(signal_id)
            if not signal:
                continue
            signal_text = " ".join(
                str(signal.get(field, ""))
                for field in ("title", "observation", "possible_angle")
            ).lower()
            if re.search(pattern, signal_text):
                hits += 1
        if hits >= 2:
            add(tag, "mecanismo (sinais)", f"presente em {hits} sinais: /{pattern}/")

    # 3. Pilares do topic.
    for pillar in topic.get("pillars") or []:
        for tag in PILLAR_TAGS.get(pillar, []):
            add(tag, f"pilar:{pillar}", f"pilar do topic ({pillar})")

    # 4. Novidade: tema revisitado ganha tag de ângulo novo.
    novelty = topic.get("novelty") or {}
    if novelty.get("verdict") == "revisited":
        add("AnguloNovo", "novidade", "tema revisitado com delta declarado")

    # 5. Fallback: derivar do título se ainda faltar.
    if len(candidates) < MIN_HASHTAGS:
        for word in re.findall(r"[A-Za-zÀ-ú]{5,}", str(topic.get("title", ""))):
            tag = _slug(word)
            if len(tag) >= 5:
                add(tag, "título", "derivado do título do tema")
            if len(candidates) >= MAX_HASHTAGS:
                break

    return candidates[:MAX_HASHTAGS]


def hashtags_for_topic(topic_id: str, *, topics_dir=None, signals_dir=None) -> list[dict]:
    topics = load_topics(topics_dir)
    if topic_id not in topics:
        raise KeyError(f"topic não encontrado: {topic_id}")
    signals = load_signals(signals_dir)
    return generate_hashtags(topics[topic_id], signals)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("topic_id", nargs="?", help="id do topic")
    parser.add_argument("--draft", help="caminho do draft (usa o nome do arquivo como topic_id)")
    parser.add_argument("--explain", action="store_true", help="mostra a origem de cada hashtag")
    args = parser.parse_args()

    topic_id = args.topic_id
    if not topic_id and args.draft:
        topic_id = Path(args.draft).stem
    if not topic_id:
        parser.print_help()
        return 2

    try:
        tags = hashtags_for_topic(topic_id)
    except KeyError as error:
        print(error)
        return 1

    if len(tags) < MIN_HASHTAGS:
        print(f"AVISO: apenas {len(tags)} hashtags (mínimo {MIN_HASHTAGS})")

    print(" ".join(t["tag"] for t in tags))
    if args.explain:
        print()
        for item in tags:
            print(f"  {item['tag']:32s} [{item['origin']}] {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
