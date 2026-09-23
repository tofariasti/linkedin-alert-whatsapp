from linkedin_alert.config import Filters
from linkedin_alert.models import Job
from linkedin_alert.whatsapp import (
    MAX_MESSAGE_CHARS,
    _callmebot_accepted,
    format_filter_block,
    format_job_messages,
    format_no_new_jobs,
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
    assert (
        "https://www.linkedin.com/jobs/search/"
        "?keywords=laravel&f_TPR=r3600&geoId=106057199&f_WT=2"
    ) in text
    assert "*2 vagas novas*" in text
    assert "*1. Desenvolvedor Laravel Pleno*" in text
    assert "Empresa: Acme Tech" in text
    assert "Candidatos: não informado" in text
    assert "Aberta desde: não informado" in text
    assert "https://www.linkedin.com/jobs/view/4469829157" in text
    assert "*2. Backend Laravel — Pagamentos*" in text


def test_job_block_includes_applicants_and_opened_at(filters: Filters) -> None:
    job = Job(
        linkedin_id="4468921714",
        title="Analista de Sistemas Sênior (PHP)",
        company="Locaweb",
        location="Brasil",
        url="https://www.linkedin.com/jobs/view/4468921714",
        applicants="Mais de 100 pessoas clicaram em Candidate-se",
        opened_at="22/09/2026 18:39 (há 16 horas)",
    )
    text = format_job_messages(filters, [job])[0]
    assert "Candidatos: Mais de 100 pessoas clicaram em Candidate-se" in text
    assert "Aberta desde: 22/09/2026 18:39 (há 16 horas)" in text


def test_single_job_title(filters: Filters, sample_jobs: list[Job]) -> None:
    messages = format_job_messages(filters, sample_jobs[:1])
    assert "*1 vaga nova*" in messages[0]
    assert "vagas novas" not in messages[0]


def test_callmebot_accepts_only_queued_success() -> None:
    queued = "<b>Message queued.</b>"
    assert _callmebot_accepted(200, queued)
    assert not _callmebot_accepted(503, "Too many requests")
    assert not _callmebot_accepted(203, "<p>Message to: +55</p>")


def test_no_new_jobs_message(filters: Filters) -> None:
    text = format_no_new_jobs(filters)
    assert text.startswith("*Filtros*")
    assert "Não houve dados novos encontrados." in text
    assert "https://www.linkedin.com/jobs/search/" in text


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
        "Recência: última hora\n"
        "Salário: qualquer\n"
        "https://www.linkedin.com/jobs/search/"
        "?keywords=laravel&f_TPR=r3600&geoId=106057199&f_WT=2"
    )
