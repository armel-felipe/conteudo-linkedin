#!/usr/bin/env python3
"""Gera o HTML navegável de temas do Bloco 1.

Lê `research/topics/topics_YYYY-MM-DD.yaml` e os arquivos de signals
correspondentes, e escreve `research/topics/topics_YYYY-MM-DD.html`.

O HTML mostra, por topic: score, critérios, tese, pergunta central, veredito de
novidade, e a **origem** — os signals que o compõem, com título, fonte e URL.

Uso:
    python scripts/generate_topics_html.py research/topics/topics_2026-09-23.yaml
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

PILLAR_LABELS = {
    "ia_aplicada": "IA Aplicada",
    "logistica_last_mile_cx": "Logística, last mile e CX",
    "lideranca_operacoes": "Liderança em operações",
    "riscos_compliance_resiliencia": "Riscos, compliance e resiliência",
    "alimentos_consumo_sustentabilidade": "Alimentos, consumo e sustentabilidade",
}

CRITERIA = [
    ("freshness", "freshness"),
    ("relevance", "relevance"),
    ("debate", "debate"),
    ("evidence", "evidence"),
    ("author_fit", "author_fit"),
    ("originality", "originality"),
    ("linkedin_fit", "linkedin_fit"),
]

VERDICT_LABELS = {
    "new": ("Novo", "new"),
    "revisited": ("Revisitado", "revisited"),
    "duplicate": ("Duplicado", "duplicate"),
}


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def load_signals(signals_dir: Path) -> dict[str, dict]:
    signals: dict[str, dict] = {}
    for path in sorted(signals_dir.glob("signals_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for signal in document.get("signals", []):
            if signal.get("id"):
                signals[signal["id"]] = signal
    return signals


def _criteria_bars(scores: dict) -> str:
    rows = []
    for key, label in CRITERIA:
        value = scores.get(key)
        if value is None:
            continue
        pct = max(0, min(100, float(value) * 10))
        rows.append(
            f'<div class="bar"><span>{_esc(label)}</span>'
            f'<div class="track"><div class="fill" style="width:{pct:.0f}%"></div></div>'
            f'<span>{_esc(value)}</span></div>'
        )
    return "\n".join(rows)


def _novelty_block(novelty: dict | None) -> str:
    if not isinstance(novelty, dict):
        return '<div class="nov missing">Sem veredito de novidade — bloqueado pelo gate.</div>'
    verdict = novelty.get("verdict", "")
    label, css = VERDICT_LABELS.get(verdict, (verdict or "?", "missing"))
    parts = [f'<span class="verdict {css}">{_esc(label)}</span>']
    if novelty.get("vs_published"):
        refs = ", ".join(_esc(t) for t in novelty["vs_published"])
        parts.append(f'<span class="vs">vs. <code>{refs}</code></span>')
    out = [f'<div class="nov">{" ".join(parts)}</div>']
    if novelty.get("delta"):
        out.append(f'<div class="delta"><b>Delta:</b> {_esc(novelty["delta"])}</div>')
    if novelty.get("new_case"):
        out.append(f'<div class="delta"><b>Evento novo:</b> {_esc(novelty["new_case"])}</div>')
    return "\n".join(out)


def _signals_block(topic: dict, signals: dict[str, dict]) -> str:
    ids = topic.get("signals") or []
    if not ids:
        return '<div class="src-empty">Sem signals registrados.</div>'
    rows = []
    for signal_id in ids:
        signal = signals.get(signal_id)
        if not signal:
            rows.append(
                f'<li class="src"><code>{_esc(signal_id)}</code> '
                f'<span class="src-missing">signal não encontrado</span></li>'
            )
            continue
        source = signal.get("source") or {}
        url = source.get("url", "")
        publisher = source.get("publisher") or source.get("type") or ""
        published = source.get("published_at", "")
        link = (
            f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(publisher)}</a>'
            if url
            else _esc(publisher)
        )
        rows.append(
            f'<li class="src">'
            f'<code>{_esc(signal_id)}</code>'
            f'<div class="src-body">'
            f'<div class="src-title">{_esc(signal.get("title", ""))}</div>'
            f'<div class="src-meta">{link}'
            f'{" · " + _esc(published) if published else ""}'
            f' · <span class="src-type">{_esc(source.get("type", ""))}</span></div>'
            f'</div></li>'
        )
    return f'<ul class="src-list">{"".join(rows)}</ul>'


def _card(topic: dict, signals: dict[str, dict], topics_file: str, signals_files: list[str]) -> str:
    scores = topic.get("scores") or {}
    total = scores.get("total")
    status = topic.get("status", "")
    css = "ready" if status == "ready_for_research" else "cand"
    pillars = "".join(
        f'<span class="pill">{_esc(PILLAR_LABELS.get(p, p))}</span>'
        for p in topic.get("pillars", [])
    )
    signal_ids = topic.get("signals") or []
    links = [f'<a href="{_esc(topics_file)}">topics yaml</a>']
    for sf in signals_files:
        links.append(f'<a href="{_esc(sf)}">signals yaml</a>')
    links.append('<a href="content/backlog.md">backlog</a>')

    return f"""
<article class="card {css}" id="{_esc(topic.get('id',''))}">
  <header class="card-head">
    <div class="score">{_esc(f"{float(total):.1f}" if total is not None else "—")}</div>
    <div class="head-main">
      <h3>{_esc(topic.get("title", ""))}</h3>
      <div class="ids">
        <code class="topic-id">{_esc(topic.get("id", ""))}</code>
        <span class="status {css}">{_esc(status)}</span>
      </div>
    </div>
  </header>
  <div class="pillars">{pillars}</div>
  <p class="thesis">{_esc(topic.get("possible_thesis", ""))}</p>
  <p class="q">{_esc(topic.get("central_question", ""))}</p>
  {_novelty_block(topic.get("novelty"))}
  <div class="bars">{_criteria_bars(scores)}</div>
  <div class="meta">
    <span><b>{len(signal_ids)}</b> sinais</span>
    <span>conexão: <b>{_esc(topic.get("author_connection", "—"))}</b></span>
  </div>
  <details class="origin" open>
    <summary>Origem — de onde vem este tema</summary>
    {_signals_block(topic, signals)}
  </details>
  <div class="links">{"".join(links)}</div>
</article>"""


def build_html(topics_path: Path) -> str:
    document = yaml.safe_load(topics_path.read_text(encoding="utf-8")) or {}
    topics = document.get("topics", [])
    date = topics_path.stem.replace("topics_", "")

    signals_dir = ROOT / "research" / "signals"
    signals = load_signals(signals_dir)
    signals_files = sorted(
        f"research/signals/{p.name}" for p in signals_dir.glob(f"signals_{date}.yaml")
    )
    topics_file = f"research/topics/{topics_path.name}"

    ready = [t for t in topics if t.get("status") == "ready_for_research"]
    others = [t for t in topics if t.get("status") != "ready_for_research"]

    cards_ready = "\n".join(_card(t, signals, topics_file, signals_files) for t in ready)
    cards_other = "\n".join(_card(t, signals, topics_file, signals_files) for t in others)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Topics {date} — Bloco 1</title>
<style>
  :root {{
    --bg:#0f1115; --panel:#171a21; --panel2:#1d2129; --line:#2a2f3a;
    --txt:#e6e9ef; --dim:#9aa3b2; --accent:#6ea8fe; --ok:#4ade80;
    --warn:#fbbf24; --bad:#f87171;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  header.page {{ padding:28px 32px 20px; border-bottom:1px solid var(--line); }}
  h1 {{ margin:0 0 6px; font-size:22px; letter-spacing:-.01em; }}
  .sub {{ color:var(--dim); font-size:13px; }}
  .sub a {{ color:var(--accent); text-decoration:none; }}
  .sub a:hover {{ text-decoration:underline; }}
  main {{ padding:24px 32px 60px; max-width:1100px; }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.06em;
    color:var(--dim); margin:30px 0 12px; font-weight:600; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
    padding:18px 20px; margin-bottom:14px; }}
  .card.ready {{ border-left:3px solid var(--ok); }}
  .card.cand {{ border-left:3px solid var(--warn); opacity:.85; }}
  .card-head {{ display:flex; gap:16px; align-items:flex-start; }}
  .score {{ font-size:26px; font-weight:700; font-variant-numeric:tabular-nums;
    min-width:62px; color:var(--accent); }}
  .card.cand .score {{ color:var(--warn); }}
  .head-main {{ flex:1; min-width:0; }}
  .head-main h3 {{ margin:0 0 6px; font-size:17px; font-weight:600; }}
  .ids {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
  .topic-id {{ font:13px ui-monospace,SFMono-Regular,Menlo,monospace;
    color:var(--accent); background:var(--panel2); border:1px solid var(--line);
    padding:2px 8px; border-radius:6px; user-select:all; }}
  .status {{ font-size:11px; padding:2px 8px; border-radius:999px;
    border:1px solid var(--line); color:var(--dim); }}
  .status.ready {{ color:var(--ok); border-color:#2f5f3f; }}
  .status.cand {{ color:var(--warn); border-color:#5f4f2f; }}
  .pillars {{ margin:12px 0 0; display:flex; gap:6px; flex-wrap:wrap; }}
  .pill {{ font-size:11px; padding:2px 8px; border-radius:999px;
    background:var(--panel2); border:1px solid var(--line); color:var(--dim); }}
  .thesis {{ margin:12px 0 0; color:#cfd6e2; }}
  .q {{ margin:8px 0 0; color:var(--dim); font-style:italic; }}
  .nov {{ margin:12px 0 0; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
  .verdict {{ font-size:11px; font-weight:600; padding:2px 9px; border-radius:999px; }}
  .verdict.new {{ background:#14351f; color:var(--ok); border:1px solid #2f5f3f; }}
  .verdict.revisited {{ background:#3a2f14; color:var(--warn); border:1px solid #5f4f2f; }}
  .verdict.duplicate {{ background:#3a1a1a; color:var(--bad); border:1px solid #5f2f2f; }}
  .verdict.missing {{ background:#3a1a1a; color:var(--bad); border:1px solid #5f2f2f; }}
  .vs {{ font-size:12px; color:var(--dim); }}
  .vs code {{ color:var(--accent); }}
  .delta {{ margin:6px 0 0; font-size:13px; color:var(--dim); }}
  .delta b {{ color:var(--txt); }}
  .missing {{ color:var(--bad); font-size:13px; }}
  .bars {{ margin-top:14px; display:grid;
    grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:6px 16px;
    font-size:12px; color:var(--dim); }}
  .bar {{ display:flex; align-items:center; gap:8px; }}
  .bar span:first-child {{ width:82px; }}
  .track {{ flex:1; height:5px; background:var(--panel2); border-radius:3px; overflow:hidden; }}
  .fill {{ height:100%; background:var(--accent); border-radius:3px; }}
  .card.cand .fill {{ background:var(--warn); }}
  .bar span:last-child {{ width:16px; text-align:right; font-variant-numeric:tabular-nums; }}
  .meta {{ margin-top:14px; padding-top:12px; border-top:1px solid var(--line);
    display:flex; gap:18px; flex-wrap:wrap; font-size:12.5px; color:var(--dim); }}
  .meta b {{ color:var(--txt); }}
  .origin {{ margin-top:12px; border-top:1px solid var(--line); padding-top:10px; }}
  .origin summary {{ cursor:pointer; font-size:12.5px; color:var(--dim);
    text-transform:uppercase; letter-spacing:.05em; }}
  .src-list {{ list-style:none; margin:10px 0 0; padding:0; }}
  .src {{ display:flex; gap:10px; padding:8px 0; border-bottom:1px dashed var(--line); }}
  .src:last-child {{ border-bottom:none; }}
  .src code {{ font:11.5px ui-monospace,SFMono-Regular,Menlo,monospace;
    color:var(--dim); min-width:150px; user-select:all; }}
  .src-body {{ flex:1; min-width:0; }}
  .src-title {{ font-size:13.5px; color:var(--txt); }}
  .src-meta {{ font-size:12px; color:var(--dim); margin-top:2px; }}
  .src-meta a {{ color:var(--accent); text-decoration:none; }}
  .src-meta a:hover {{ text-decoration:underline; }}
  .src-type {{ color:#7c8698; }}
  .src-missing {{ color:var(--bad); font-size:12px; }}
  .src-empty {{ color:var(--dim); font-size:13px; }}
  .links {{ margin-top:12px; display:flex; gap:14px; flex-wrap:wrap; font-size:12.5px; }}
  .links a {{ color:var(--accent); text-decoration:none; }}
  .links a:hover {{ text-decoration:underline; }}
  .note {{ background:var(--panel2); border:1px solid var(--line); border-radius:10px;
    padding:14px 16px; color:var(--dim); font-size:13px; }}
  .note b {{ color:var(--txt); }}
</style>
</head>
<body>
<header class="page">
  <h1>Topics — leva {date}</h1>
  <div class="sub">
    {len(topics)} topics · <b style="color:var(--ok)">{len(ready)} ready_for_research</b> ·
    <b style="color:var(--warn)">{len(others)} candidate</b><br>
    Artefatos: <a href="{_esc(topics_file)}">{_esc(topics_path.name)}</a>
    {" · ".join(f'<a href="{_esc(sf)}">{_esc(Path(sf).name)}</a>' for sf in signals_files)}
    · <a href="content/backlog.md">content/backlog.md</a>
  </div>
</header>
<main>
<h2>Fila do Bloco 2 — ready_for_research</h2>
{cards_ready or '<div class="note">Nenhum tema ready_for_research.</div>'}
<h2>Fora do backlog — candidate</h2>
{cards_other or '<div class="note">Nenhum tema candidate.</div>'}
<h2>Como ler esta página</h2>
<div class="note">
  Cada card traz o <code>topic_id</code> (copiável) e a <b>origem</b>: os signals que
  compõem o tema, com título, fonte e link. O bloco <b>novidade</b> mostra o veredito do
  gate: <b>Novo</b> (fenômeno inédito), <b>Revisitado</b> (com delta declarado) ou
  <b>Duplicado</b> (bloqueado). O gate é fail-closed: sem veredito válido, o tema não
  entra no Bloco 2.
</div>
</main>
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    topics_path = Path(sys.argv[1])
    if not topics_path.is_absolute():
        topics_path = ROOT / topics_path
    if not topics_path.exists():
        print(f"não encontrado: {topics_path}")
        return 1
    output = topics_path.with_suffix(".html")
    output.write_text(build_html(topics_path), encoding="utf-8")
    print(f"escrito: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
