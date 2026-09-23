from __future__ import annotations

import argparse
import logging
import sys

from linkedin_alert.config import Settings, load_settings
from linkedin_alert.db import connect, mark_notified, pending_jobs, upsert_jobs
from linkedin_alert.linkedin import SessionExpiredError, scrape_jobs
from linkedin_alert.whatsapp import (
    WhatsAppError,
    format_job_messages,
    format_no_new_jobs,
    format_session_expired,
    send_message,
    send_messages,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca vagas e avisa no WhatsApp")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape + grava no SQLite e imprime o lote; não envia WhatsApp",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()

    try:
        jobs = scrape_jobs(settings)
    except SessionExpiredError as exc:
        logger.error("%s", exc)
        if settings.notify_on_session_expired and not args.dry_run:
            _notify_session_expired(settings)
        return 1

    conn = connect(settings.database)
    try:
        inserted = upsert_jobs(conn, jobs)
        pending = pending_jobs(conn)

        if args.dry_run:
            logger.info(
                "Dry-run: %s extraídas, %s novas no banco, %s pendentes de WhatsApp",
                len(jobs),
                len(inserted),
                len(pending),
            )
            messages = format_job_messages(settings.filters, inserted)
            if not messages:
                print(format_no_new_jobs(settings.filters))
                return 0
            for message in messages:
                print(message)
                print("---")
            return 0

        if not pending:
            logger.info("Nenhuma vaga nova para notificar")
            if not _notify_no_new_jobs(settings):
                return 1
            return 0

        messages = format_job_messages(settings.filters, pending)
        try:
            send_messages(settings.phone, settings.api_key, messages)
        except WhatsAppError:
            logger.exception("Falha no CallMeBot; vagas permanecem pendentes")
            return 1

        mark_notified(conn, [job.linkedin_id for job in pending])
        logger.info("Notificadas %s vagas", len(pending))
        return 0
    finally:
        conn.close()


def _notify_no_new_jobs(settings: Settings) -> bool:
    try:
        send_message(
            settings.phone,
            settings.api_key,
            format_no_new_jobs(settings.filters),
        )
    except WhatsAppError:
        logger.exception("Falha no CallMeBot ao avisar busca sem dados novos")
        return False
    return True


def _notify_session_expired(settings: Settings) -> None:
    try:
        send_message(
            settings.phone,
            settings.api_key,
            format_session_expired(settings.filters),
        )
    except WhatsAppError:
        logger.exception("Não foi possível avisar sessão expirada no WhatsApp")


if __name__ == "__main__":
    sys.exit(main())
