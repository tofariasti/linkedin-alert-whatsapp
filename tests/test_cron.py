from pathlib import Path

from linkedin_alert.config import Filters, Settings
from linkedin_alert.cron import cron_line, format_crontab_block


def test_cron_line_uses_flock_and_log(tmp_path: Path) -> None:
    settings = Settings(
        filters=Filters("laravel", "Brasil", "106057199", "remote", "1h"),
        phone="5551989030405",
        api_key="",
        cron="0 * * * *",
        schedule_description="A cada 1 hora",
        timezone="America/Sao_Paulo",
        database=tmp_path / "jobs.db",
        storage_state=tmp_path / "storage_state.json",
        log=tmp_path / "cron.log",
        lock=tmp_path / "lock",
        notify_on_session_expired=True,
        root=tmp_path,
    )
    line = cron_line(settings, python=Path("/opt/venv/bin/python"))
    assert line.startswith("0 * * * * ")
    assert "TZ=America/Sao_Paulo" in line
    assert "flock -n" in line
    assert str(settings.lock) in line
    assert "/opt/venv/bin/python -m linkedin_alert" in line
    assert f">> {settings.log} 2>&1" in line

    block = format_crontab_block(settings, python=Path("/opt/venv/bin/python"))
    assert "# linkedin-alert-whatsapp start" in block
    assert "# A cada 1 hora" in block
