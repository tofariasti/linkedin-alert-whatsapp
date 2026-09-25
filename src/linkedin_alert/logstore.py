from __future__ import annotations

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOG_KEEP = 3
RUN_START = "---------- início ----------"
RUN_END = "---------- fim ----------"
_DAY_LOG = re.compile(r"^\d{4}-\d{2}-\d{2}\.log$")
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def daily_log_path(
    directory: Path,
    timezone: str,
    now: datetime | None = None,
) -> Path:
    moment = now or datetime.now(ZoneInfo(timezone))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    day = moment.astimezone(ZoneInfo(timezone)).date()
    return directory / f"{day.isoformat()}.log"


def prune_logs(
    directory: Path,
    keep: int = LOG_KEEP,
    extra: Path | None = None,
) -> None:
    """Keep the newest dated logs. `extra` counts even before the file exists."""
    directory.mkdir(parents=True, exist_ok=True)
    files = [path for path in directory.glob("*.log") if _DAY_LOG.match(path.name)]
    names = {path.name for path in files}
    if extra is not None and extra.name not in names and _DAY_LOG.match(extra.name):
        files.append(extra)
    files.sort(key=lambda path: path.name)
    for old in files[:-keep] if keep > 0 else files:
        if old.exists():
            old.unlink()


def configure_logging(
    directory: Path,
    timezone: str,
    now: datetime | None = None,
) -> Path:
    path = daily_log_path(directory, timezone, now)
    prune_logs(directory, extra=path)
    handlers: list[logging.Handler] = [
        logging.FileHandler(path, encoding="utf-8"),
    ]
    if sys.stderr.isatty():
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format=_FORMAT,
        handlers=handlers,
        force=True,
    )
    return path


def log_run_start() -> None:
    logging.getLogger("linkedin_alert").info("%s", RUN_START)


def log_run_end() -> None:
    logging.getLogger("linkedin_alert").info("%s", RUN_END)
