import sqlite3
from pathlib import Path

from linkedin_alert.db import connect, mark_notified, pending_jobs, upsert_jobs
from linkedin_alert.models import Job


def test_upsert_dedup_and_pending(db_path: Path, sample_jobs: list[Job]) -> None:
    conn = connect(db_path)
    first = upsert_jobs(conn, sample_jobs)
    assert [job.linkedin_id for job in first] == ["4469829157", "4470012345"]

    second = upsert_jobs(conn, sample_jobs)
    assert second == []

    pending = pending_jobs(conn)
    assert len(pending) == 2

    mark_notified(conn, ["4469829157"])
    pending = pending_jobs(conn)
    assert [job.linkedin_id for job in pending] == ["4470012345"]

    mark_notified(conn, ["4470012345"])
    assert pending_jobs(conn) == []
    conn.close()


def test_upsert_keeps_applicants_and_opened_at(db_path: Path) -> None:
    job = Job(
        linkedin_id="4468921714",
        title="Analista",
        company="Locaweb",
        location="Brasil",
        url="https://www.linkedin.com/jobs/view/4468921714",
        applicants="Mais de 100 pessoas clicaram em Candidate-se",
        opened_at="22/09/2026 18:39 (há 16 horas)",
    )
    conn = connect(db_path)
    upsert_jobs(conn, [job])
    pending = pending_jobs(conn)
    assert pending[0].applicants == job.applicants
    assert pending[0].opened_at == job.opened_at
    conn.close()


def test_connect_adds_meta_columns_to_existing_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(db_path)
    raw.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            linkedin_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            notified_at TEXT
        )
        """
    )
    raw.commit()
    raw.close()

    conn = connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    assert "applicants" in columns
    assert "opened_at" in columns
    conn.close()


def test_failed_notify_stays_pending(db_path: Path, sample_jobs: list[Job]) -> None:
    conn = connect(db_path)
    upsert_jobs(conn, sample_jobs)
    # Simulate CallMeBot failure: do not call mark_notified
    assert len(pending_jobs(conn)) == 2
    conn.close()
