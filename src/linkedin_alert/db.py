from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from linkedin_alert.models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linkedin_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    notified_at TEXT,
    applicants TEXT NOT NULL DEFAULT '',
    opened_at TEXT NOT NULL DEFAULT ''
);
"""


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    _ensure_job_columns(conn)
    return conn


def upsert_jobs(conn: sqlite3.Connection, jobs: list[Job]) -> list[Job]:
    """Insert unseen jobs. Returns only the rows inserted in this call."""
    now = _now()
    inserted: list[Job] = []
    for job in jobs:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO jobs (
                linkedin_id, title, company, location, url, first_seen_at,
                applicants, opened_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.linkedin_id,
                job.title,
                job.company,
                job.location,
                job.url,
                now,
                job.applicants,
                job.opened_at,
            ),
        )
        if cur.rowcount:
            inserted.append(job)
    conn.commit()
    return inserted


def pending_jobs(conn: sqlite3.Connection) -> list[Job]:
    rows = conn.execute(
        """
        SELECT linkedin_id, title, company, location, url, applicants, opened_at
        FROM jobs
        WHERE notified_at IS NULL
        ORDER BY id
        """
    ).fetchall()
    return [
        Job(
            linkedin_id=row["linkedin_id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            url=row["url"],
            applicants=row["applicants"],
            opened_at=row["opened_at"],
        )
        for row in rows
    ]


def mark_notified(conn: sqlite3.Connection, linkedin_ids: list[str]) -> None:
    if not linkedin_ids:
        return
    now = _now()
    conn.executemany(
        "UPDATE jobs SET notified_at = ? WHERE linkedin_id = ? AND notified_at IS NULL",
        [(now, job_id) for job_id in linkedin_ids],
    )
    conn.commit()


def _ensure_job_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "applicants" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN applicants TEXT NOT NULL DEFAULT ''")
    if "opened_at" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN opened_at TEXT NOT NULL DEFAULT ''")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
