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


def test_recency_30m_maps_to_half_hour() -> None:
    filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="any",
        recency="30m",
    )
    assert filters.f_tpr == "r1800"
    assert filters.recency_label == "últimos 30 minutos"
    assert "f_TPR=r1800" in build_search_url(filters)


def test_build_search_url_omits_workplace_when_any() -> None:
    filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="any",
        recency="24h",
    )
    url = build_search_url(filters)
    assert "keywords=laravel" in url
    assert "f_TPR=r86400" in url
    assert "geoId=106057199" in url
    assert "f_WT" not in url


def test_build_search_url_includes_salary_range() -> None:
    filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="any",
        recency="1h",
        salary="f_SA_id_225001:272001",
    )
    url = build_search_url(filters)
    assert "f_TPR=r3600" in url
    assert "geoId=106057199" in url
    assert "f_SAL=f_SA_id_225001%3A272001" in url
    assert "f_WT" not in url


EXACT_ALERT_URL = (
    "https://www.linkedin.com/jobs/search-results/?currentJobId=4468921714"
    "&keywords=laravel&origin=SEMANTIC_SEARCH_JOB_ALERT_IN_APP_NOTIFICATION"
    "&originToLandingJobPostings=4468921714%2C4470662296%2C4468939639"
    "&geoId=106057199&f_TPR=a1790071915-"
)


def test_build_search_url_keeps_exact_alert_url() -> None:
    filters = Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="any",
        recency="1h",
        salary="f_SA_id_225001:272001",
        search_url=EXACT_ALERT_URL,
    )
    assert build_search_url(filters) == EXACT_ALERT_URL
    assert filters.keywords_label == "laravel"
    assert filters.workplace_label == "qualquer"
    assert filters.recency_label == "desde 22/09/2026 07:11"
    assert filters.salary_label == "qualquer"


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
phone = "5511999999999"

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
    assert settings.phone == "5511999999999"
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


def test_load_settings_rejects_bad_search_url(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        """
[filters]
keywords = "laravel"
country = "Brasil"
geo_id = "106057199"
workplace = "remote"
recency = "1h"
search_url = "https://example.com/jobs"
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
    with pytest.raises(ValueError, match="search_url"):
        load_settings(tmp_path)
