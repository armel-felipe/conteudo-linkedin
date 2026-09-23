#!/usr/bin/env python3
"""hashtags.py — Gera hashtags para um draft a partir das fontes do topic.

As hashtags são **trazidas pelas fontes**: cada sinal carrega
`source.source_hashtags`, extraídas do post/artigo original. O gerador
prioriza essas hashtags reais e só recorre a vocabulário derivado do tema
quando a fonte não trouxe nenhuma.

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
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
TOPICS_DIR = ROOT / "research" / "topics"
SIGNALS_DIR = ROOT / "research" / "signals"

MIN_HASHTAGS = 3
MAX_HASHTAGS = 5

# Ruído de plataforma: hashtags de alcance que não descrevem o tema.
NOISE = re.compile(
    r"^#(x27|x200B|fyp|foryou|viral|vibe|techtok|trend|explore|"
    r"japanesecooking|garbagegold|dumpsterdiv\w*|managersbelike|corporatelife|"
    r"workplace|kitchenhacks|freezerhacks|foodhacks|foodstorage|groce\w*|"
    r"easypeasyguide|thematrix|savehumanity|nottoolate|robot|survey\w*|"
    r"womenintech|aipoweredwomen|business|productivity|aitools|automation)$",
    re.IGNORECASE,
)

# Ruído de identidade: cargo, nome de programa/marca ou hashtag genérica
# que não descreve o fenômeno do tema.
IDENTITY_NOISE = re.compile(
    r"^#(coo|ceo|cto|cfo|founders?|startups?|businesstips|lostintech|"
    r"agentverify|owasp)$",
    re.IGNORECASE,
)

# Vocabulário de fallback, usado só quando a fonte não trouxe hashtags.
# Ancorado no domínio do tema, não em palavras genéricas.
PILLAR_TAGS = {
    "ia_aplicada": ["IAAplicada", "AgentesDeIA", "IAEmProducao"],
    "logistica_last_mile_cx": ["UltimaMilha", "Logistica", "ExperienciaDoCliente"],
    "lideranca_operacoes": ["LiderancaOperacional", "Accountability", "GestaoDeTimes"],
    "riscos_compliance_resiliencia": ["GovernancaDeIA", "Compliance", "ResilienciaOperacional"],
    "alimentos_consumo_sustentabilidade": ["CadeiaAlimentar", "Sustentabilidade", "Desperdicio"],
}

MECHANISM_TAGS = {
    r"prova de entrega|proof of delivery|status de entrega|marcad[oa] como entregue": "ProvaDeEntrega",
    r"custo (da|por|unitári|operacion)|margem|economia unit": "CustoOperacional",
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


def _normalize_tag(tag: str) -> str:
    """Normaliza a hashtag da fonte para PascalCase consistente."""
    body = tag.lstrip("#")
    return "#" + _slug(body)


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


def _core_text(topic: dict) -> str:
    return " ".join(
        str(topic.get(field, ""))
        for field in ("title", "possible_thesis", "central_question")
    ).lower()


def source_hashtags(topic: dict, signals: dict[str, dict]) -> list[dict]:
    """Hashtags trazidas pelas fontes dos sinais do topic, por frequência."""
    counter: Counter[str] = Counter()
    origins: dict[str, list[str]] = {}
    for signal_id in topic.get("signals") or []:
        signal = signals.get(signal_id)
        if not signal:
            continue
        tags = (signal.get("source") or {}).get("source_hashtags") or []
        for tag in tags:
            if NOISE.match(tag) or IDENTITY_NOISE.match(tag):
                continue
            normalized = _normalize_tag(tag)
            # Descarta truncamentos da fonte (ex.: "#Accounta").
            if len(normalized) < 6:
                continue
            counter[normalized] += 1
            origins.setdefault(normalized, []).append(signal_id)

    # Remove truncamentos: uma tag que é prefixo de outra mais longa e
    # aparece menos vezes é ruído de corte da fonte.
    tags_sorted = sorted(counter, key=len, reverse=True)
    for tag in list(counter):
        body = tag.lstrip("#").lower()
        for longer in tags_sorted:
            longer_body = longer.lstrip("#").lower()
            if longer_body != body and longer_body.startswith(body):
                del counter[tag]
                origins.pop(tag, None)
                break

    return [
        {
            "tag": tag,
            "origin": "fonte",
            "reason": f"trazida por {len(origins[tag])} sinal(is): {', '.join(origins[tag])}",
        }
        for tag, _ in counter.most_common()
    ]


def fallback_hashtags(topic: dict, signals: dict[str, dict]) -> list[dict]:
    """Vocabulário derivado do tema, usado só quando a fonte não trouxe nada."""
    core = _core_text(topic)
    candidates: list[dict] = []
    seen: set[str] = set()

    def add(tag: str, origin: str, reason: str) -> None:
        if tag in seen:
            return
        seen.add(tag)
        candidates.append({"tag": f"#{tag}", "origin": origin, "reason": reason})

    for pattern, tag in MECHANISM_TAGS.items():
        if re.search(pattern, core):
            add(tag, "mecanismo (núcleo)", f"presente no título/tese: /{pattern}/")

    for pillar in topic.get("pillars") or []:
        for tag in PILLAR_TAGS.get(pillar, []):
            add(tag, f"pilar:{pillar}", f"pilar do topic ({pillar})")

    if len(candidates) < MIN_HASHTAGS:
        for word in re.findall(r"[A-Za-zÀ-ú]{5,}", str(topic.get("title", ""))):
            tag = _slug(word)
            if len(tag) >= 5:
                add(tag, "título", "derivado do título do tema")
            if len(candidates) >= MAX_HASHTAGS:
                break

    return candidates


def generate_hashtags(topic: dict, signals: dict[str, dict]) -> list[dict]:
    """Hashtags do topic: fontes primeiro, fallback do tema se faltar.

    Retorna lista de {tag, origin, reason}. Entre 3 e 5 itens.
    """
    from_source = source_hashtags(topic, signals)
    chosen = from_source[:MAX_HASHTAGS]

    if len(chosen) < MIN_HASHTAGS:
        seen = {c["tag"] for c in chosen}
        for item in fallback_hashtags(topic, signals):
            if item["tag"] in seen:
                continue
            chosen.append(item)
            seen.add(item["tag"])
            if len(chosen) >= MAX_HASHTAGS:
                break

    return chosen[:MAX_HASHTAGS]


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
