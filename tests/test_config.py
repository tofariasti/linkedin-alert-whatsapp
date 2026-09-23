from pathlib import Path

import pytest

from linkedin_alert.config import Filters, build_search_url, load_settings


def test_build_search_url_maps_filters() -> None:
    filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="remote",
        recency="1h",
    )
    url = build_search_url(filters)
    assert url.startswith("https://www.linkedin.com/jobs/search/?")
    assert "keywords=laravel" in url
    assert "f_TPR=r3600" in url
    assert "geoId=106057199" in url
    assert "f_WT=2" in url


def test_load_settings_from_repo_config(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        """
[filters]
keywords = "django"
country = "Brasil"
geo_id = "106057199"
workplace = "hybrid"
recency = "12h"

[whatsapp]
phone = "5551989030405"

[schedule]
cron = "0 * * * *"
description = "A cada 1 hora"
timezone = "America/Sao_Paulo"

[paths]
database = "data/jobs.db"
storage_state = "storage_state.json"
log = "data/cron.log"
lock = "data/linkedin_alert.lock"

[alerts]
notify_on_session_expired = true
""",
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.filters.keywords == "django"
    assert settings.filters.f_wt == "3"
    assert settings.filters.f_tpr == "r43200"
    assert settings.phone == "5551989030405"
    assert settings.database == tmp_path / "data" / "jobs.db"


def test_load_settings_rejects_bad_workplace(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        """
[filters]
keywords = "laravel"
country = "Brasil"
geo_id = "106057199"
workplace = "anywhere"
recency = "1h"
[whatsapp]
phone = "1"
[schedule]
cron = "* * * * *"
[paths]
database = "a"
storage_state = "b"
log = "c"
lock = "d"
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="workplace"):
        load_settings(tmp_path)
