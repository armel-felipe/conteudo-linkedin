"""Testes de slots e clusters de agendamento (scheduling_slots.py).

Regra (config/scheduling.yaml): dias úteis (seg-sex), janela 10:00–12:00,
padrão 10:00, no máximo 1 post por dia, com exceções declaradas.
"""

from datetime import date, time

import pytest

from scheduling_slots import (
    available_slots,
    check_schedule,
    clusters,
    is_weekday,
    load_config,
    occupied_days,
    parse_timestamp,
    validate_slot,
    valid_times,
)

# Config de teste: sem exceções, para exercitar a regra pura.
CONFIG = {
    "rules": {
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "window": {"start": "10:00", "end": "12:00"},
        "default_time": "10:00",
        "step_minutes": 30,
        "max_per_day": 1,
    },
    "exceptions": [],
}


# --- regra do slot --------------------------------------------------------


def test_weekday_is_valid():
    # 2026-09-25 é sexta
    assert validate_slot(date(2026, 9, 25), time(10, 0), config=CONFIG) == []


def test_saturday_is_invalid():
    problems = validate_slot(date(2026, 9, 26), time(10, 0), config=CONFIG)
    assert problems
    assert "Saturday" in problems[0]


def test_sunday_is_invalid():
    problems = validate_slot(date(2026, 9, 27), time(10, 0), config=CONFIG)
    assert problems
    assert "Sunday" in problems[0]


def test_time_before_window_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(9, 30), config=CONFIG)
    assert problems
    assert "fora da janela" in problems[0]


def test_time_after_window_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(12, 30), config=CONFIG)
    assert problems
    assert "fora da janela" in problems[0]


def test_window_bounds_are_inclusive():
    assert validate_slot(date(2026, 9, 25), time(10, 0), config=CONFIG) == []
    assert validate_slot(date(2026, 9, 25), time(12, 0), config=CONFIG) == []


def test_off_granularity_is_invalid():
    problems = validate_slot(date(2026, 9, 25), time(10, 15), config=CONFIG)
    assert problems
    assert "granularidade" in problems[0]


def test_valid_times_cover_window():
    times = valid_times(config=CONFIG)
    assert times[0] == time(10, 0)
    assert times[-1] == time(12, 0)
    assert time(10, 30) in times
    assert time(11, 0) in times


def test_is_weekday():
    assert is_weekday(date(2026, 9, 25), config=CONFIG)  # sexta
    assert not is_weekday(date(2026, 9, 26), config=CONFIG)  # sábado


# --- exceções declaradas --------------------------------------------------


def test_declared_exception_allows_weekend():
    config = {
        "rules": CONFIG["rules"],
        "exceptions": [
            {"topic_id": "topic_x", "date": "2026-09-26", "reason": "decisão do autor"}
        ],
    }
    assert validate_slot(date(2026, 9, 26), time(10, 0), config=config, topic_id="topic_x") == []


def test_exception_does_not_apply_to_other_topic():
    config = {
        "rules": CONFIG["rules"],
        "exceptions": [
            {"topic_id": "topic_x", "date": "2026-09-26", "reason": "decisão do autor"}
        ],
    }
    problems = validate_slot(date(2026, 9, 26), time(10, 0), config=config, topic_id="topic_y")
    assert problems


def test_exception_does_not_apply_to_other_date():
    config = {
        "rules": CONFIG["rules"],
        "exceptions": [
            {"topic_id": "topic_x", "date": "2026-09-26", "reason": "decisão do autor"}
        ],
    }
    problems = validate_slot(date(2026, 10, 3), time(10, 0), config=config, topic_id="topic_x")
    assert problems


def test_load_config_reads_repo_file():
    config = load_config()
    assert config["rules"]["max_per_day"] == 1
    assert config["rules"]["default_time"] == "10:00"
    assert any(e["topic_id"] == "topic_20260915_06" for e in config["exceptions"])


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
        config=CONFIG,
    )
    days = [s["date"] for s in slots]
    assert days == [date(2026, 9, 25), date(2026, 9, 29)]
    assert date(2026, 9, 26) not in days  # sábado
    assert date(2026, 9, 27) not in days  # domingo


def test_available_slots_uses_requested_time():
    slots = available_slots(
        date(2026, 9, 25), date(2026, 9, 25), occupied=set(), at=time(11, 30), config=CONFIG
    )
    assert slots[0]["time"] == time(11, 30)


def test_available_slots_rejects_invalid_time():
    with pytest.raises(ValueError, match="hora inválida"):
        available_slots(
            date(2026, 9, 25), date(2026, 9, 25), occupied=set(), at=time(13, 0), config=CONFIG
        )


def test_available_slots_rejects_reversed_range():
    with pytest.raises(ValueError, match="end must not be before start"):
        available_slots(date(2026, 9, 29), date(2026, 9, 25), occupied=set(), config=CONFIG)


def test_available_slots_default_time_from_config():
    slots = available_slots(date(2026, 9, 25), date(2026, 9, 25), occupied=set(), config=CONFIG)
    assert slots[0]["time"] == time(10, 0)


# --- clusters -------------------------------------------------------------


def _slot(day):
    return {"date": day, "time": time(10, 0), "weekday": day.strftime("%A")}


def test_clusters_groups_consecutive_weekdays():
    slots = [_slot(date(2026, 9, 28)), _slot(date(2026, 9, 29)), _slot(date(2026, 9, 30))]
    groups = clusters(slots, config=CONFIG)
    assert len(groups) == 1
    assert len(groups[0]) == 3


def test_clusters_treats_friday_and_monday_as_consecutive():
    """Fim de semana não quebra o cluster: sexta e segunda são consecutivos."""
    slots = [_slot(date(2026, 9, 25)), _slot(date(2026, 9, 28))]
    groups = clusters(slots, config=CONFIG)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_clusters_splits_on_gap():
    slots = [_slot(date(2026, 9, 25)), _slot(date(2026, 9, 30))]
    groups = clusters(slots, config=CONFIG)
    assert len(groups) == 2


def test_clusters_empty():
    assert clusters([], config=CONFIG) == []


# --- check da agenda ------------------------------------------------------


def _post(topic_id, day, at):
    return {
        "topic_id": topic_id,
        "file": f"content/published/{topic_id}.md",
        "date": day,
        "time": at,
        "raw": f"{day.isoformat()}T{at.strftime('%H:%M')} America/Sao_Paulo",
    }


def test_check_schedule_flags_weekend():
    violations = check_schedule([_post("topic_x", date(2026, 9, 26), time(10, 0))], config=CONFIG)
    assert len(violations) == 1
    assert violations[0]["topic_id"] == "topic_x"


def test_check_schedule_passes_valid_posts():
    assert check_schedule([_post("topic_y", date(2026, 9, 25), time(10, 30))], config=CONFIG) == []


def test_check_schedule_flags_more_than_one_post_per_day():
    posts = [
        _post("a", date(2026, 9, 25), time(10, 0)),
        _post("b", date(2026, 9, 25), time(11, 0)),
    ]
    violations = check_schedule(posts, config=CONFIG)
    assert len(violations) == 1
    assert "limite é 1 por dia" in violations[0]["problems"][0]


def test_check_schedule_allows_declared_exception():
    config = {
        "rules": CONFIG["rules"],
        "exceptions": [
            {"topic_id": "topic_x", "date": "2026-09-26", "reason": "decisão do autor"}
        ],
    }
    posts = [_post("topic_x", date(2026, 9, 26), time(10, 0))]
    assert check_schedule(posts, config=config) == []


def test_occupied_days():
    posts = [
        {"date": date(2026, 9, 25)},
        {"date": date(2026, 9, 25)},
        {"date": date(2026, 9, 29)},
    ]
    assert occupied_days(posts) == {date(2026, 9, 25), date(2026, 9, 29)}
