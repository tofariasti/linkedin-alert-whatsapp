from pathlib import Path

import pytest

from linkedin_alert.config import Filters
from linkedin_alert.models import Job


@pytest.fixture
def filters() -> Filters:
    return Filters(
        keywords="laravel",
        country="Brasil",
        geo_id="106057199",
        workplace="remote",
        recency="1h",
    )


@pytest.fixture
def sample_jobs() -> list[Job]:
    return [
        Job(
            linkedin_id="4469829157",
            title="Desenvolvedor Laravel Pleno",
            company="Acme Tech",
            location="Brasil (Remoto)",
            url="https://www.linkedin.com/jobs/view/4469829157",
        ),
        Job(
            linkedin_id="4470012345",
            title="Backend Laravel — Pagamentos",
            company="FinApp",
            location="São Paulo (Remoto)",
            url="https://www.linkedin.com/jobs/view/4470012345",
        ),
    ]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "jobs.db"
