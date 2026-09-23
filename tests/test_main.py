from pathlib import Path
from unittest.mock import MagicMock, patch

from linkedin_alert.config import Filters
from linkedin_alert.db import connect, mark_notified, upsert_jobs
from linkedin_alert.linkedin import SessionExpiredError
from linkedin_alert.models import Job


def test_dry_run_prints_only_inserted_jobs(
    tmp_path: Path, sample_jobs: list[Job]
) -> None:
    from linkedin_alert import __main__ as main_mod

    settings = MagicMock()
    settings.database = tmp_path / "jobs.db"
    settings.filters.keywords = "laravel"
    settings.filters.country = "Brasil"
    settings.filters.workplace_label = "remoto"
    settings.filters.recency_label = "última hora"

    with (
        patch.object(main_mod, "load_settings", return_value=settings),
        patch.object(main_mod, "scrape_jobs", return_value=sample_jobs),
    ):
        assert main_mod.main(["--dry-run"]) == 0
        assert main_mod.main(["--dry-run"]) == 0


def test_no_new_jobs_sends_whatsapp_notice(tmp_path: Path) -> None:
    from linkedin_alert import __main__ as main_mod

    settings = MagicMock()
    settings.database = tmp_path / "jobs.db"
    settings.phone = "555189030405"
    settings.api_key = "key"
    settings.filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="remote",
        recency="1h",
    )

    with (
        patch.object(main_mod, "load_settings", return_value=settings),
        patch.object(main_mod, "scrape_jobs", return_value=[]),
        patch.object(main_mod, "send_message") as send,
    ):
        assert main_mod.main([]) == 0

    send.assert_called_once()
    assert send.call_args.args[0] == settings.phone
    text = send.call_args.args[2]
    assert "Não houve dados novos encontrados." in text
    assert "busca anterior" not in text


def test_no_new_jobs_includes_last_stored_job(
    tmp_path: Path, sample_jobs: list[Job]
) -> None:
    from linkedin_alert import __main__ as main_mod

    settings = MagicMock()
    settings.database = tmp_path / "jobs.db"
    settings.phone = "555189030405"
    settings.api_key = "key"
    settings.filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="remote",
        recency="1h",
    )
    conn = connect(settings.database)
    upsert_jobs(conn, sample_jobs)
    mark_notified(conn, [job.linkedin_id for job in sample_jobs])
    conn.close()

    with (
        patch.object(main_mod, "load_settings", return_value=settings),
        patch.object(main_mod, "scrape_jobs", return_value=[]),
        patch.object(main_mod, "send_message") as send,
    ):
        assert main_mod.main([]) == 0

    text = send.call_args.args[2]
    assert "*Último registro (busca anterior)*" in text
    assert sample_jobs[-1].title in text


def test_dry_run_without_new_jobs_does_not_notify(tmp_path: Path) -> None:
    from linkedin_alert import __main__ as main_mod

    settings = MagicMock()
    settings.database = tmp_path / "jobs.db"
    settings.filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="remote",
        recency="1h",
    )

    with (
        patch.object(main_mod, "load_settings", return_value=settings),
        patch.object(main_mod, "scrape_jobs", return_value=[]),
        patch.object(main_mod, "send_message") as send,
    ):
        assert main_mod.main(["--dry-run"]) == 0

    send.assert_not_called()


def test_missing_session_exits_without_whatsapp(tmp_path: Path) -> None:
    from linkedin_alert import __main__ as main_mod

    settings = MagicMock()
    settings.notify_on_session_expired = True
    settings.database = tmp_path / "jobs.db"

    with (
        patch.object(main_mod, "load_settings", return_value=settings),
        patch.object(
            main_mod,
            "scrape_jobs",
            side_effect=SessionExpiredError("Sessão não encontrada"),
        ),
        patch.object(main_mod, "_notify_session_expired") as notify,
    ):
        assert main_mod.main(["--dry-run"]) == 1
        notify.assert_not_called()
