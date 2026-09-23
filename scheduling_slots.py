#!/usr/bin/env python3
"""scheduling_slots.py — Slots e clusters de agendamento do LinkedIn.

Regra de agendamento:
  - Dias: segunda a sexta (fins de semana não são slots válidos).
  - Horário padrão: 10:00, podendo oscilar até 12:00 (janela 10:00–12:00).

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

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
MARKER_RE = re.compile(r"<!--\s*agendado:\s*([^>]+?)\s*-->")

# Janela permitida de horário.
WINDOW_START = time(10, 0)
WINDOW_END = time(12, 0)
DEFAULT_TIME = time(10, 0)
# Granularidade aceita dentro da janela.
STEP_MINUTES = 30

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def is_weekday(day: date) -> bool:
    return day.weekday() < 5


def valid_times() -> list[time]:
    """Horários válidos na janela, na granularidade de 30 minutos."""
    out = []
    current = datetime.combine(date(2000, 1, 1), WINDOW_START)
    end = datetime.combine(date(2000, 1, 1), WINDOW_END)
    while current <= end:
        out.append(current.time())
        current += timedelta(minutes=STEP_MINUTES)
    return out


def validate_slot(day: date, at: time) -> list[str]:
    """Problemas que tornam o slot inválido. Lista vazia = válido."""
    problems = []
    if not is_weekday(day):
        problems.append(f"{day.isoformat()} é {day.strftime('%A')} — fora de segunda a sexta")
    if at < WINDOW_START or at > WINDOW_END:
        problems.append(
            f"{at.strftime('%H:%M')} fora da janela "
            f"{WINDOW_START.strftime('%H:%M')}–{WINDOW_END.strftime('%H:%M')}"
        )
    elif at.minute % STEP_MINUTES != 0:
        problems.append(
            f"{at.strftime('%H:%M')} não está na granularidade de {STEP_MINUTES} minutos"
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
    at: time = DEFAULT_TIME,
    include_start: bool = True,
) -> list[dict]:
    """Dias úteis livres entre `start` e `end` (inclusive), com a hora pedida."""
    if end < start:
        raise ValueError("end must not be before start")
    problems = validate_slot(start, at)
    if problems:
        raise ValueError(f"hora inválida: {', '.join(problems)}")

    slots = []
    day = start
    while day <= end:
        if is_weekday(day) and day not in occupied:
            slots.append({"date": day, "time": at, "weekday": day.strftime("%A")})
        day += timedelta(days=1)
    return slots


def clusters(slots: list[dict]) -> list[list[dict]]:
    """Agrupa slots em blocos de dias úteis consecutivos.

    Fins de semana não quebram um cluster: sexta e segunda são consecutivos
    no calendário de trabalho.
    """
    if not slots:
        return []
    ordered = sorted(slots, key=lambda s: s["date"])
    groups: list[list[dict]] = [[ordered[0]]]
    for slot in ordered[1:]:
        previous = groups[-1][-1]["date"]
        # próximo dia útil depois de `previous`
        nxt = previous + timedelta(days=1)
        while not is_weekday(nxt):
            nxt += timedelta(days=1)
        if slot["date"] == nxt:
            groups[-1].append(slot)
        else:
            groups.append([slot])
    return groups


def check_schedule(posts: list[dict]) -> list[dict]:
    """Violações da regra na agenda atual."""
    violations = []
    for post in posts:
        problems = validate_slot(post["date"], post["time"])
        if problems:
            violations.append({
                "topic_id": post["topic_id"],
                "file": post["file"],
                "raw": post["raw"],
                "problems": problems,
            })
    return violations


def _fmt_slot(slot: dict) -> str:
    return f"{slot['date'].isoformat()} {slot['time'].strftime('%H:%M')} ({slot['weekday']})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="start", help="data inicial (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end", help="data final (YYYY-MM-DD)")
    parser.add_argument("--count", type=int, help="número de slots a listar")
    parser.add_argument("--time", default="10:00", help="hora do slot (padrão 10:00)")
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
        problems = validate_slot(day, at)
        if problems:
            print(f"INVÁLIDO: {args.validate}")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print(f"VÁLIDO: {args.validate} ({day.strftime('%A')})")
        return 0

    posts = scan_scheduled()
    occupied = occupied_days(posts)

    if args.check:
        violations = check_schedule(posts)
        print(f"Posts agendados: {len(posts)}")
        if violations:
            print("\nVIOLAÇÕES DA REGRA DE AGENDAMENTO:")
            for v in violations:
                print(f"  {v['topic_id']} ({v['raw']})")
                for problem in v["problems"]:
                    print(f"      - {problem}")
            print("\nFALHA: há agendamentos fora da regra (seg-sex, 10:00–12:00).")
            return 1
        print("OK: todos os agendamentos estão dentro da regra.")
        return 0

    at = datetime.strptime(args.time, "%H:%M").time()
    start = date.fromisoformat(args.start) if args.start else date.today()
    if args.end:
        end = date.fromisoformat(args.end)
    elif args.count:
        end = start + timedelta(days=args.count * 3 + 7)
    else:
        end = start + timedelta(days=30)

    slots = available_slots(start, end, occupied, at=at)
    if args.count:
        slots = slots[: args.count]

    print(f"Ocupados: {len(occupied)} dias ({', '.join(sorted(d.isoformat() for d in occupied))})")
    print(f"Slots livres ({at.strftime('%H:%M')}): {len(slots)}")
    for slot in slots:
        print(f"  - {_fmt_slot(slot)}")

    if args.clusters:
        groups = clusters(slots)
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
