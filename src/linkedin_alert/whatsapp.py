from __future__ import annotations

import logging

import requests

from linkedin_alert.config import Filters, build_search_url
from linkedin_alert.models import Job

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
# CallMeBot costuma falhar em silêncio acima de ~1k; o teste curto deles funciona.
MAX_MESSAGE_CHARS = 800


class WhatsAppError(Exception):
    """CallMeBot rejected or failed to send a message."""


def format_filter_block(filters: Filters) -> str:
    return (
        "*Filtros*\n"
        f"Palavra-chave: {filters.keywords_label}\n"
        f"País: {filters.country}\n"
        f"Modalidade: {filters.workplace_label}\n"
        f"Recência: {filters.recency_label}\n"
        f"Salário: {filters.salary_label}\n"
        f"{build_search_url(filters)}"
    )


def format_job_block(job: Job, index: int) -> str:
    applicants = job.applicants or "não informado"
    opened_at = job.opened_at or "não informado"
    return (
        f"*{index}. {job.title}*\n"
        f"Empresa: {job.company}\n"
        f"Local: {job.location}\n"
        f"Candidatos: {applicants}\n"
        f"Aberta desde: {opened_at}\n"
        f"{job.url}"
    )


def format_no_new_jobs(filters: Filters) -> str:
    return (
        f"{format_filter_block(filters)}\n\n"
        "*LinkedIn Alert*\n"
        "Não houve dados novos encontrados."
    )


def format_session_expired(filters: Filters) -> str:
    return (
        f"{format_filter_block(filters)}\n\n"
        "*LinkedIn Alert*\n"
        "Sessão expirada. Rode: python -m linkedin_alert.login"
    )


def format_job_messages(filters: Filters, jobs: list[Job]) -> list[str]:
    """One WhatsApp message per cycle, split if over MAX_MESSAGE_CHARS."""
    if not jobs:
        return []

    header = format_filter_block(filters)
    chunks: list[str] = []
    current: list[Job] = []

    def render(batch: list[Job]) -> str:
        count = len(batch)
        title = "*1 vaga nova*" if count == 1 else f"*{count} vagas novas*"
        body = "\n\n".join(
            format_job_block(job, index) for index, job in enumerate(batch, start=1)
        )
        return f"{header}\n\n{title}\n\n{body}"

    for job in jobs:
        candidate = [*current, job]
        if current and len(render(candidate)) > MAX_MESSAGE_CHARS:
            chunks.append(render(current))
            current = [job]
        else:
            current = candidate

    if current:
        chunks.append(render(current))
    return chunks


def send_message(phone: str, api_key: str, text: str) -> None:
    if not api_key:
        msg = "CALLMEBOT_APIKEY ausente no .env"
        raise WhatsAppError(msg)
    response = requests.get(
        CALLMEBOT_URL,
        params={"phone": phone, "text": text, "apikey": api_key},
        timeout=30,
    )
    body = (response.text or "").strip()
    if not _callmebot_accepted(response.status_code, body):
        msg = f"CallMeBot HTTP {response.status_code}: {body[:300]}"
        raise WhatsAppError(msg)
    logger.info("CallMeBot OK (%s chars): %s", len(text), body[:200])


def _callmebot_accepted(status_code: int, body: str) -> bool:
    if status_code >= 400:
        return False
    low = body.lower()
    return "queued" in low or "success" in low


def send_messages(phone: str, api_key: str, texts: list[str]) -> int:
    """Send messages in order. Returns how many were accepted."""
    sent = 0
    for text in texts:
        send_message(phone, api_key, text)
        sent += 1
    return sent
