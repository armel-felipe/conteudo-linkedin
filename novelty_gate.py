"""Gate de novidade editorial do Bloco 1.

Impede que um topic recrie um tema já publicado ou arquivado sem declarar um
delta verificável. A duplicação aqui é conceitual, não textual: dois textos
podem tratar do mesmo fenômeno sem compartilhar palavras nem fontes. Por isso
o gate não tenta "detectar duplicata" de forma automática — ele exige que o
topic **declare** contra o que está sendo comparado e qual é a diferença, e
bloqueia (fail-closed) quando a declaração não se sustenta.

Camadas:
  1. `detect_overlap`  — sinaliza candidatos por similaridade lexical (não decide).
  2. `validate_novelty` — exige o campo `novelty` e valida o delta declarado.
  3. `is_eligible`      — fail-closed: só passa quem tem veredito válido.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

VERDICTS = ("new", "revisited", "duplicate")

# Um delta precisa de substância mínima para não ser uma frase de fachada.
MIN_DELTA_CHARS = 60

# Acima deste Jaccard lexical o gate sugere revisão (não bloqueia sozinho).
OVERLAP_HINT = 0.30

_STOPWORDS = {
    "para", "como", "quando", "onde", "porque", "sobre", "entre", "depois",
    "antes", "ainda", "mais", "menos", "pode", "precisa", "deve", "fazer",
    "faz", "ser", "estar", "tem", "ter", "isso", "esse", "essa", "este",
    "esta", "pelo", "pela", "dos", "das", "uma", "não", "sim", "que", "com",
    "sem", "por", "sua", "seu", "nas", "nos", "aos", "ele", "ela", "mas",
    "também", "muito", "todo", "toda", "cada", "outro", "outra", "mesmo",
    "mesma", "apenas", "então", "assim", "aqui", "ali", "vai", "vir", "dar",
    "ver", "ler", "agir", "ação", "ações", "caso", "casos", "forma", "parte",
    "vez", "vezes", "ponto", "coisa", "coisas", "gente", "pessoa", "pessoas",
    "tempo", "dia", "dias", "ano", "anos", "mês", "meses", "semana", "horas",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-záàâãéêíóôõúç]{4,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _signature(topic: dict) -> set[str]:
    text = " ".join(
        str(topic.get(field, ""))
        for field in ("title", "possible_thesis", "central_question")
    )
    return _tokens(text)


def load_published_topics(topics_dir) -> dict[str, dict]:
    """Topics com status `published` ou `archived` em `topics_*.yaml`."""
    published: dict[str, dict] = {}
    for path in sorted(Path(topics_dir).glob("topics_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for topic in document.get("topics", []):
            if topic.get("status") in ("published", "archived"):
                topic_id = topic.get("id") or topic.get("topic_id")
                if topic_id:
                    published[topic_id] = topic
    return published


def detect_overlap(topic: dict, published: dict[str, dict]) -> list[tuple[float, str]]:
    """Candidatos a sobreposição por similaridade lexical, do maior para o menor.

    Sinaliza para revisão humana/adversarial. Não decide nada sozinho.
    """
    signature = _signature(topic)
    if not signature:
        return []
    scored = []
    for topic_id, other in published.items():
        other_signature = _signature(other)
        if not other_signature:
            continue
        union = signature | other_signature
        if not union:
            continue
        scored.append((len(signature & other_signature) / len(union), topic_id))
    scored.sort(reverse=True)
    return scored


def _delta_is_substantive(delta: str, published_thesis: str) -> bool:
    """O delta precisa ser longo o bastante e não ser a tese antiga reescrita."""
    if len(delta.strip()) < MIN_DELTA_CHARS:
        return False
    delta_tokens = _tokens(delta)
    thesis_tokens = _tokens(published_thesis)
    if not delta_tokens:
        return False
    if not thesis_tokens:
        return True
    # Se o delta é quase todo composto de termos da tese antiga, é reescrita.
    return len(delta_tokens & thesis_tokens) / len(delta_tokens) < 0.75


def validate_novelty(topic: dict, published: dict[str, dict]) -> list[str]:
    """Problemas que impedem o topic de ser elegível. Lista vazia = ok."""
    problems: list[str] = []
    novelty = topic.get("novelty")

    if not isinstance(novelty, dict):
        return ["campo `novelty` ausente ou inválido"]

    verdict = novelty.get("verdict")
    if verdict not in VERDICTS:
        problems.append(f"`novelty.verdict` deve ser um de {VERDICTS}, veio {verdict!r}")

    vs_published = novelty.get("vs_published") or []
    if not isinstance(vs_published, list):
        problems.append("`novelty.vs_published` deve ser uma lista de topic ids")
        vs_published = []

    unknown = [tid for tid in vs_published if tid not in published]
    if unknown:
        problems.append(f"`novelty.vs_published` cita topic inexistente: {', '.join(unknown)}")

    if verdict == "duplicate":
        problems.append("topic marcado como `duplicate` — não entra no backlog")

    if verdict == "new" and vs_published:
        problems.append("veredito `new` não pode declarar `vs_published`")

    if verdict == "revisited":
        if not vs_published:
            problems.append("veredito `revisited` exige `vs_published`")
        delta = novelty.get("delta") or ""
        if not delta.strip():
            problems.append("veredito `revisited` exige `delta` declarado")
        else:
            for topic_id in vs_published:
                other = published.get(topic_id)
                if not other:
                    continue
                if not _delta_is_substantive(delta, other.get("possible_thesis", "")):
                    problems.append(
                        f"`delta` não se sustenta contra {topic_id}: "
                        "curto demais ou é a tese anterior reescrita"
                    )

    return problems


def is_eligible(topic: dict, published: dict[str, dict]) -> bool:
    """Fail-closed: elegível apenas quando não há nenhum problema."""
    return not validate_novelty(topic, published)
