#!/usr/bin/env python3
"""scheduling_slots.py — Slots e clusters de agendamento do LinkedIn.

Regra de agendamento (config/scheduling.yaml):
  - Dias: segunda a sexta (fins de semana não são slots válidos).
  - Horário padrão: 10:00, podendo oscilar até 12:00 (janela 10:00–12:00).
  - Máximo de 1 post por dia.
  - Exceções declaradas em config/scheduling.yaml (nunca silenciosas).

Conceitos:
  - **Slot**: par (data, hora) válido pela regra e ainda livre.
  - **Cluster**: sequência de dias úteis livres e consecutivos.

Uso:
  # Slots livres nos próximos dias
  python scheduling_slots.py --from 2026-09-23 --to 2026-10-15

  # Próximos N slots, com hora específica
  python scheduling_slots.py --count 5 --time 10:30

  # Validar a agenda atual contra a regra (falha se houver violação)
  python scheduling_slots.py --check

  # Validar um slot específico
  python scheduling_slots.py --validate 2026-09-26T10:00
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
CONFIG = ROOT / "config" / "scheduling.yaml"
MARKER_RE = re.compile(r"<!--\s*agendado:\s*([^>]+?)\s*-->")

# Valores padrão, usados quando config/scheduling.yaml não existe.
DEFAULT_RULES = {
    "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "window": {"start": "10:00", "end": "12:00"},
    "default_time": "10:00",
    "step_minutes": 30,
    "max_per_day": 1,
}


def load_config(path: Path | None = None) -> dict:
    """Carrega config/scheduling.yaml, com fallback para os padrões."""
    config_path = path or CONFIG
    if not config_path.exists():
        return {"rules": dict(DEFAULT_RULES), "exceptions": []}
    document = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    rules = {**DEFAULT_RULES, **(document.get("rules") or {})}
    return {"rules": rules, "exceptions": document.get("exceptions") or []}


def _parse_time(raw: str) -> time:
    return datetime.strptime(str(raw), "%H:%M").time()


def _rules(config: dict) -> dict:
    rules = config["rules"]
    return {
        "weekdays": set(rules["weekdays"]),
        "window_start": _parse_time(rules["window"]["start"]),
        "window_end": _parse_time(rules["window"]["end"]),
        "default_time": _parse_time(rules["default_time"]),
        "step_minutes": int(rules["step_minutes"]),
        "max_per_day": int(rules["max_per_day"]),
    }


def _exception_for(config: dict, topic_id: str, day: date) -> dict | None:
    for exception in config.get("exceptions") or []:
        if exception.get("topic_id") != topic_id:
            continue
        raw_date = exception.get("date")
        if raw_date and str(raw_date) == day.isoformat():
            return exception
    return None


def is_weekday(day: date, config: dict | None = None) -> bool:
    rules = _rules(config or load_config())
    return day.strftime("%A") in rules["weekdays"]


def valid_times(config: dict | None = None) -> list[time]:
    """Horários válidos na janela, na granularidade configurada."""
    rules = _rules(config or load_config())
    out = []
    current = datetime.combine(date(2000, 1, 1), rules["window_start"])
    end = datetime.combine(date(2000, 1, 1), rules["window_end"])
    while current <= end:
        out.append(current.time())
        current += timedelta(minutes=rules["step_minutes"])
    return out


def validate_slot(
    day: date,
    at: time,
    *,
    config: dict | None = None,
    topic_id: str | None = None,
) -> list[str]:
    """Problemas que tornam o slot inválido. Lista vazia = válido.

    Uma exceção declarada em config/scheduling.yaml para (topic_id, day)
    dispensa a checagem de dia da semana e de janela de horário.
    """
    config = config or load_config()
    rules = _rules(config)

    if topic_id and _exception_for(config, topic_id, day):
        return []

    problems = []
    if day.strftime("%A") not in rules["weekdays"]:
        problems.append(
            f"{day.isoformat()} é {day.strftime('%A')} — fora de "
            f"{', '.join(sorted(rules['weekdays']))}"
        )
    if at < rules["window_start"] or at > rules["window_end"]:
        problems.append(
            f"{at.strftime('%H:%M')} fora da janela "
            f"{rules['window_start'].strftime('%H:%M')}–{rules['window_end'].strftime('%H:%M')}"
        )
    elif at.minute % rules["step_minutes"] != 0:
        problems.append(
            f"{at.strftime('%H:%M')} não está na granularidade de {rules['step_minutes']} minutos"
        )
    return problems


def parse_timestamp(raw: str) -> tuple[date, time] | None:
    """Extrai (data, hora) de '2026-09-10T10:00 America/Sao_Paulo'."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", raw.strip())
    if not match:
        return None
    day = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    at = datetime.strptime(match.group(2), "%H:%M").time()
    return day, at


def scan_scheduled(content_dir: Path | None = None) -> list[dict]:
    """Posts com marker de agendamento, em content/."""
    content = content_dir or CONTENT
    posts = []
    for folder in ("drafts", "published", "approved", "arquived"):
        directory = content / folder
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for marker in MARKER_RE.findall(text):
                parsed = parse_timestamp(marker)
                if not parsed:
                    continue
                day, at = parsed
                posts.append({
                    "topic_id": path.stem,
                    "folder": folder,
                    "file": str(path.relative_to(content.parent)),
                    "date": day,
                    "time": at,
                    "raw": marker.strip(),
                })
    return posts


def occupied_days(posts: list[dict]) -> set[date]:
    return {p["date"] for p in posts}


def available_slots(
    start: date,
    end: date,
    occupied: set[date],
    *,
    at: time | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Dias úteis livres entre `start` e `end` (inclusive), com a hora pedida.

    Um dia com qualquer post agendado está ocupado: a regra é no máximo
    `max_per_day` post por dia (padrão 1).
    """
    config = config or load_config()
    rules = _rules(config)
    at = at or rules["default_time"]

    if end < start:
        raise ValueError("end must not be before start")
    problems = validate_slot(start, at, config=config)
    if problems:
        raise ValueError(f"hora inválida: {', '.join(problems)}")

    slots = []
    day = start
    while day <= end:
        if day.strftime("%A") in rules["weekdays"] and day not in occupied:
            slots.append({"date": day, "time": at, "weekday": day.strftime("%A")})
        day += timedelta(days=1)
    return slots


def clusters(slots: list[dict], config: dict | None = None) -> list[list[dict]]:
    """Agrupa slots em blocos de dias úteis consecutivos.

    Fins de semana não quebram um cluster: sexta e segunda são consecutivos
    no calendário de trabalho.
    """
    if not slots:
        return []
    config = config or load_config()
    rules = _rules(config)
    ordered = sorted(slots, key=lambda s: s["date"])
    groups: list[list[dict]] = [[ordered[0]]]
    for slot in ordered[1:]:
        previous = groups[-1][-1]["date"]
        # próximo dia útil depois de `previous`
        nxt = previous + timedelta(days=1)
        while nxt.strftime("%A") not in rules["weekdays"]:
            nxt += timedelta(days=1)
        if slot["date"] == nxt:
            groups[-1].append(slot)
        else:
            groups.append([slot])
    return groups


def check_schedule(posts: list[dict], config: dict | None = None) -> list[dict]:
    """Violações da regra na agenda atual.

    Verifica a regra de slot por post (com exceções declaradas) e o limite
    de posts por dia.
    """
    config = config or load_config()
    rules = _rules(config)
    violations = []

    for post in posts:
        problems = validate_slot(
            post["date"], post["time"], config=config, topic_id=post.get("topic_id")
        )
        if problems:
            violations.append({
                "topic_id": post["topic_id"],
                "file": post["file"],
                "raw": post["raw"],
                "problems": problems,
            })

    # Limite de posts por dia.
    by_day: dict[date, list[dict]] = {}
    for post in posts:
        by_day.setdefault(post["date"], []).append(post)
    for day, group in sorted(by_day.items()):
        if len(group) > rules["max_per_day"]:
            violations.append({
                "topic_id": ", ".join(p["topic_id"] for p in group),
                "file": ", ".join(p["file"] for p in group),
                "raw": day.isoformat(),
                "problems": [
                    f"{len(group)} posts em {day.isoformat()} — "
                    f"o limite é {rules['max_per_day']} por dia"
                ],
            })

    return violations


def _fmt_slot(slot: dict) -> str:
    return f"{slot['date'].isoformat()} {slot['time'].strftime('%H:%M')} ({slot['weekday']})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="start", help="data inicial (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end", help="data final (YYYY-MM-DD)")
    parser.add_argument("--count", type=int, help="número de slots a listar")
    parser.add_argument("--time", help="hora do slot (padrão: default_time da config)")
    parser.add_argument("--topic", help="topic_id, para aplicar exceções declaradas")
    parser.add_argument("--check", action="store_true", help="valida a agenda atual contra a regra")
    parser.add_argument("--validate", help="valida um slot específico (YYYY-MM-DDTHH:MM)")
    parser.add_argument("--clusters", action="store_true", help="mostra os clusters de dias livres")
    args = parser.parse_args()

    if args.validate:
        parsed = parse_timestamp(args.validate)
        if not parsed:
            print(f"formato inválido: {args.validate} (use YYYY-MM-DDTHH:MM)")
            return 2
        day, at = parsed
        problems = validate_slot(day, at, topic_id=args.topic)
        if problems:
            print(f"INVÁLIDO: {args.validate}")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print(f"VÁLIDO: {args.validate} ({day.strftime('%A')})")
        return 0

    config = load_config()
    posts = scan_scheduled()
    occupied = occupied_days(posts)

    if args.check:
        violations = check_schedule(posts, config=config)
        print(f"Posts agendados: {len(posts)}")
        exceptions = config.get("exceptions") or []
        if exceptions:
            print(f"Exceções declaradas: {len(exceptions)}")
            for exception in exceptions:
                print(
                    f"  - {exception.get('topic_id')} em {exception.get('date')}: "
                    f"{exception.get('reason', '')}"
                )
        if violations:
            print("\nVIOLAÇÕES DA REGRA DE AGENDAMENTO:")
            for v in violations:
                print(f"  {v['topic_id']} ({v['raw']})")
                for problem in v["problems"]:
                    print(f"      - {problem}")
            print("\nFALHA: há agendamentos fora da regra.")
            return 1
        print("OK: todos os agendamentos estão dentro da regra.")
        return 0

    at = datetime.strptime(args.time, "%H:%M").time() if args.time else None
    start = date.fromisoformat(args.start) if args.start else date.today()
    if args.end:
        end = date.fromisoformat(args.end)
    elif args.count:
        end = start + timedelta(days=args.count * 3 + 7)
    else:
        end = start + timedelta(days=30)

    slots = available_slots(start, end, occupied, at=at, config=config)
    if args.count:
        slots = slots[: args.count]

    shown_time = (at or _rules(config)["default_time"]).strftime("%H:%M")
    print(f"Ocupados: {len(occupied)} dias ({', '.join(sorted(d.isoformat() for d in occupied))})")
    print(f"Slots livres ({shown_time}): {len(slots)}")
    for slot in slots:
        print(f"  - {_fmt_slot(slot)}")

    if args.clusters:
        groups = clusters(slots, config=config)
        print(f"\nClusters de dias consecutivos: {len(groups)}")
        for index, group in enumerate(groups, start=1):
            first, last = group[0], group[-1]
            print(
                f"  {index}. {len(group)} dia(s): "
                f"{first['date'].isoformat()} → {last['date'].isoformat()}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
