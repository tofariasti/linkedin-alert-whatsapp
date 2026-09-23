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


def test_failed_notify_stays_pending(db_path: Path, sample_jobs: list[Job]) -> None:
    conn = connect(db_path)
    upsert_jobs(conn, sample_jobs)
    # Simulate CallMeBot failure: do not call mark_notified
    assert len(pending_jobs(conn)) == 2
    conn.close()
