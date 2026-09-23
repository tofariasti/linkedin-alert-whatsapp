from __future__ import annotations

import logging
from urllib.parse import urlencode

import requests

from linkedin_alert.config import Filters
from linkedin_alert.models import Job

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
MAX_MESSAGE_CHARS = 1500


class WhatsAppError(Exception):
    """CallMeBot rejected or failed to send a message."""


def format_filter_block(filters: Filters) -> str:
    return (
        "*Filtros*\n"
        f"Palavra-chave: {filters.keywords}\n"
        f"País: {filters.country}\n"
        f"Modalidade: {filters.workplace_label}\n"
        f"Recência: {filters.recency_label}"
    )


def format_job_block(job: Job, index: int) -> str:
    return (
        f"*{index}. {job.title}*\n"
        f"Empresa: {job.company}\n"
        f"Local: {job.location}\n"
        f"{job.url}"
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
    params = {"phone": phone, "text": text, "apikey": api_key}
    url = f"{CALLMEBOT_URL}?{urlencode(params)}"
    response = requests.get(url, timeout=30)
    if response.status_code >= 400:
        msg = f"CallMeBot HTTP {response.status_code}: {response.text[:200]}"
        raise WhatsAppError(msg)
    body = response.text.lower()
    if "error" in body and "queued" not in body and "success" not in body:
        logger.warning("CallMeBot respondeu: %s", response.text[:300])
    logger.info("Mensagem enviada via CallMeBot (%s chars)", len(text))


def send_messages(phone: str, api_key: str, texts: list[str]) -> int:
    """Send messages in order. Returns how many were accepted."""
    sent = 0
    for text in texts:
        send_message(phone, api_key, text)
        sent += 1
    return sent
