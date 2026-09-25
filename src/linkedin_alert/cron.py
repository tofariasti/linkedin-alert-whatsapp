from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from linkedin_alert.config import Settings, load_settings

logger = logging.getLogger(__name__)

MARKER_START = "# linkedin-alert-whatsapp start"
MARKER_END = "# linkedin-alert-whatsapp end"


def cron_line(
    settings: Settings,
    python: Path | None = None,
    expression: str | None = None,
) -> str:
    python = python or Path(sys.executable)
    flock = shutil.which("flock") or "flock"
    settings.lock.parent.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    schedule = expression if expression is not None else settings.cron[0]
    # Cron has no polkit agent. systemd-inhibit there exits before the search
    # and the WhatsApp is never sent. The idle lock is a user unit, not this line.
    # % must be escaped: crontab turns a bare % into a newline.
    return (
        f"{schedule} "
        f"TZ={settings.timezone} "
        f"{flock} -n {settings.lock} "
        f"{python} -m linkedin_alert "
        f">> {settings.log_dir}/$(date +\\%F).log 2>&1"
    )


def format_crontab_block(settings: Settings, python: Path | None = None) -> str:
    lines = "\n".join(cron_line(settings, python, expr) for expr in settings.cron)
    return (
        f"{MARKER_START}\n"
        f"# {settings.schedule_description}\n"
        f"{lines}\n"
        f"{MARKER_END}\n"
    )


def upsert_crontab(block: str) -> None:
    current = _read_crontab()
    if MARKER_START in current and MARKER_END in current:
        start = current.index(MARKER_START)
        end = current.index(MARKER_END) + len(MARKER_END)
        # keep surrounding newlines tidy
        updated = (
            current[:start].rstrip("\n") + "\n\n" + block + current[end:].lstrip("\n")
        )
        if not updated.endswith("\n"):
            updated += "\n"
    else:
        updated = current.rstrip("\n")
        if updated:
            updated += "\n\n"
        updated += block
        if not updated.endswith("\n"):
            updated += "\n"

    subprocess.run(
        ["crontab", "-"],
        input=updated,
        text=True,
        check=True,
    )


def _read_crontab() -> str:
    result = subprocess.run(
        ["crontab", "-l"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "no crontab" in stderr:
            return ""
        raise RuntimeError(result.stderr.strip() or "falha ao ler crontab")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Gera ou instala o bloco do cron")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print", action="store_true", dest="do_print")
    group.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)

    settings = load_settings()
    block = format_crontab_block(settings)

    if args.do_print:
        print(block, end="")
        return 0

    upsert_crontab(block)
    logger.info("Crontab do usuário atualizado (não use root)")
    print(block, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
