"""Testes de slots e clusters de agendamento (scheduling_slots.py).

Regra: dias úteis (seg-sex), horário padrão 10:00, janela 10:00–12:00.
"""

from datetime import date, time

import pytest

from scheduling_slots import (
    DEFAULT_TIME,
    available_slots,
    check_schedule,
    clusters,
    is_weekday,
    occupied_days,
    parse_timestamp,
    validate_slot,
    valid_times,
)


# --- regra do slot --------------------------------------------------------


def test_weekday_is_valid():
    # 2026-09-25 é sexta
    assert validate_slot(date(2026, 9, 25), time(10, 0)) == []


def test_saturday_is_invalid():
    problems = validate_slot(date(2026, 9, 26), time(10, 0))
    assert problems
    assert "Saturday" in problems[0]


def test_sunday_is_invalid():
    problems = validate_slot(date(2026, 9, 27), time(10, 0))
    assert problems
    assert "Sunday" in problems[0]


def test_time_before_window_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(9, 30))
    assert problems
    assert "fora da janela" in problems[0]


def test_time_after_window_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(12, 30))
    assert problems
    assert "fora da janela" in problems[0]


def test_window_bounds_are_inclusive():
    assert validate_slot(date(2026, 9, 25), time(10, 0)) == []
    assert validate_slot(date(2026, 9, 25), time(12, 0)) == []


def test_off_granularity_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(10, 15))
    assert problems
    assert "granularidade" in problems[0]


def test_valid_times_cover_window():
    times = valid_times()
    assert times[0] == time(10, 0)
    assert times[-1] == time(12, 0)
    assert time(10, 30) in times
    assert time(11, 0) in times


def test_is_weekday():
    assert is_weekday(date(2026, 9, 25))  # sexta
    assert not is_weekday(date(2026, 9, 26))  # sábado


# --- parse de timestamp ---------------------------------------------------


def test_parse_timestamp_with_timezone():
    parsed = parse_timestamp("2026-09-10T10:00 America/Sao_Paulo")
    assert parsed == (date(2026, 9, 10), time(10, 0))


def test_parse_timestamp_invalid_returns_none():
    assert parse_timestamp("amanhã às 10h") is None


# --- slots disponíveis ----------------------------------------------------


def test_available_slots_skips_weekends_and_occupied():
    slots = available_slots(
        date(2026, 9, 25),  # sexta
        date(2026, 9, 29),  # terça
        occupied={date(2026, 9, 28)},  # segunda ocupada
    )
    days = [s["date"] for s in slots]
    assert days == [date(2026, 9, 25), date(2026, 9, 29)]
    assert date(2026, 9, 26) not in days  # sábado
    assert date(2026, 9, 27) not in days  # domingo


def test_available_slots_uses_requested_time():
    slots = available_slots(date(2026, 9, 25), date(2026, 9, 25), occupied=set(), at=time(11, 30))
    assert slots[0]["time"] == time(11, 30)


def test_available_slots_rejects_invalid_time():
    with pytest.raises(ValueError, match="hora inválida"):
        available_slots(date(2026, 9, 25), date(2026, 9, 25), occupied=set(), at=time(13, 0))


def test_available_slots_rejects_reversed_range():
    with pytest.raises(ValueError, match="end must not be before start"):
        available_slots(date(2026, 9, 29), date(2026, 9, 25), occupied=set())


def test_default_time_is_ten():
    assert DEFAULT_TIME == time(10, 0)


# --- clusters -------------------------------------------------------------


def _slot(day):
    return {"date": day, "time": time(10, 0), "weekday": day.strftime("%A")}


def test_clusters_groups_consecutive_weekdays():
    slots = [_slot(date(2026, 9, 28)), _slot(date(2026, 9, 29)), _slot(date(2026, 9, 30))]
    groups = clusters(slots)
    assert len(groups) == 1
    assert len(groups[0]) == 3


def test_clusters_treats_friday_and_monday_as_consecutive():
    """Fim de semana não quebra o cluster: sexta e segunda são consecutivos."""
    slots = [_slot(date(2026, 9, 25)), _slot(date(2026, 9, 28))]
    groups = clusters(slots)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_clusters_splits_on_gap():
    slots = [_slot(date(2026, 9, 25)), _slot(date(2026, 9, 30))]
    groups = clusters(slots)
    assert len(groups) == 2


def test_clusters_empty():
    assert clusters([]) == []


# --- check da agenda ------------------------------------------------------


def test_check_schedule_flags_weekend():
    posts = [{
        "topic_id": "topic_x",
        "file": "content/published/topic_x.md",
        "date": date(2026, 9, 26),
        "time": time(10, 0),
        "raw": "2026-09-26T10:00 America/Sao_Paulo",
    }]
    violations = check_schedule(posts)
    assert len(violations) == 1
    assert violations[0]["topic_id"] == "topic_x"


def test_check_schedule_passes_valid_posts():
    posts = [{
        "topic_id": "topic_y",
        "file": "content/published/topic_y.md",
        "date": date(2026, 9, 25),
        "time": time(10, 30),
        "raw": "2026-09-25T10:30 America/Sao_Paulo",
    }]
    assert check_schedule(posts) == []


def test_occupied_days():
    posts = [
        {"date": date(2026, 9, 25)},
        {"date": date(2026, 9, 25)},
        {"date": date(2026, 9, 29)},
    ]
    assert occupied_days(posts) == {date(2026, 9, 25), date(2026, 9, 29)}
