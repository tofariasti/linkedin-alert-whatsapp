from linkedin_alert.config import Filters
from linkedin_alert.models import Job
from linkedin_alert.whatsapp import (
    MAX_MESSAGE_CHARS,
    format_filter_block,
    format_job_messages,
    format_session_expired,
)


def test_filter_block_comes_first(filters: Filters, sample_jobs: list[Job]) -> None:
    messages = format_job_messages(filters, sample_jobs)
    assert len(messages) == 1
    text = messages[0]
    assert text.startswith("*Filtros*")
    assert "Palavra-chave: laravel" in text
    assert "País: Brasil" in text
    assert "Modalidade: remoto" in text
    assert "Recência: última hora" in text
    assert "*2 vagas novas*" in text
    assert "*1. Desenvolvedor Laravel Pleno*" in text
    assert "Empresa: Acme Tech" in text
    assert "https://www.linkedin.com/jobs/view/4469829157" in text
    assert "*2. Backend Laravel — Pagamentos*" in text


def test_single_job_title(filters: Filters, sample_jobs: list[Job]) -> None:
    messages = format_job_messages(filters, sample_jobs[:1])
    assert "*1 vaga nova*" in messages[0]
    assert "vagas novas" not in messages[0]


def test_session_expired_starts_with_filters(filters: Filters) -> None:
    text = format_session_expired(filters)
    assert text.startswith("*Filtros*")
    assert "python -m linkedin_alert.login" in text


def test_split_repeats_filters(filters: Filters) -> None:
    jobs = [
        Job(
            linkedin_id=str(i),
            title="A" * 80,
            company="Empresa longa " + ("X" * 40),
            location="Brasil (Remoto)",
            url=f"https://www.linkedin.com/jobs/view/{i}",
        )
        for i in range(20)
    ]
    messages = format_job_messages(filters, jobs)
    assert len(messages) >= 2
    for message in messages:
        assert message.startswith("*Filtros*")
        assert "Palavra-chave: laravel" in message
        assert len(message) <= MAX_MESSAGE_CHARS + 50  # header + last job slack


def test_filter_block_labels(filters: Filters) -> None:
    block = format_filter_block(filters)
    assert block == (
        "*Filtros*\n"
        "Palavra-chave: laravel\n"
        "País: Brasil\n"
        "Modalidade: remoto\n"
        "Recência: última hora"
    )
