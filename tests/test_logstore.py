from datetime import datetime
from zoneinfo import ZoneInfo

from linkedin_alert.logstore import (
    RUN_END,
    RUN_START,
    configure_logging,
    daily_log_path,
    log_run_end,
    log_run_start,
    prune_logs,
)

_SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def test_daily_log_uses_sao_paulo_date(tmp_path) -> None:
    # 02:00 UTC is still the previous evening in São Paulo.
    moment = datetime(2026, 9, 24, 2, 0, tzinfo=ZoneInfo("UTC"))
    path = daily_log_path(tmp_path, "America/Sao_Paulo", moment)
    assert path.name == "2026-09-23.log"


def test_prune_keeps_three_newest_and_reserves_today(tmp_path) -> None:
    for name in (
        "2026-09-20.log",
        "2026-09-21.log",
        "2026-09-22.log",
        "2026-09-23.log",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep", encoding="utf-8")
    today = tmp_path / "2026-09-24.log"

    prune_logs(tmp_path, extra=today)

    remaining = sorted(path.name for path in tmp_path.glob("*.log"))
    assert remaining == ["2026-09-22.log", "2026-09-23.log"]
    assert (tmp_path / "notes.txt").exists()
    assert not today.exists()


def test_configure_logging_writes_today_and_drops_the_oldest(tmp_path) -> None:
    for name in (
        "2026-09-20.log",
        "2026-09-21.log",
        "2026-09-22.log",
        "2026-09-23.log",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    now = datetime(2026, 9, 24, 9, 0, tzinfo=_SAO_PAULO)

    path = configure_logging(tmp_path, "America/Sao_Paulo", now)

    names = sorted(item.name for item in tmp_path.glob("*.log"))
    assert names == ["2026-09-22.log", "2026-09-23.log", "2026-09-24.log"]
    assert path == tmp_path / "2026-09-24.log"
    assert path.exists()


def test_run_markers_open_and_close_the_log(tmp_path) -> None:
    now = datetime(2026, 9, 24, 9, 0, tzinfo=_SAO_PAULO)
    path = configure_logging(tmp_path, "America/Sao_Paulo", now)
    log_run_start()
    log_run_end()
    text = path.read_text(encoding="utf-8")
    assert RUN_START in text
    assert text.index(RUN_START) < text.index(RUN_END)
