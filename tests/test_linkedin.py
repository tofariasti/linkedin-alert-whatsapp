from datetime import datetime
from zoneinfo import ZoneInfo

from linkedin_alert.linkedin import parse_listing_meta

_NOW = datetime(2026, 9, 23, 10, 39, tzinfo=ZoneInfo("America/Sao_Paulo"))


def test_parse_listing_meta_from_job_header() -> None:
    applicants, opened_at = parse_listing_meta(
        "Brasil · há 16 horas · Mais de 100 pessoas clicaram em Candidate-se",
        _NOW,
    )
    assert applicants == "Mais de 100 pessoas clicaram em Candidate-se"
    assert opened_at == "22/09/2026 18:39 (há 16 horas)"


def test_parse_listing_meta_ignores_easy_apply_label() -> None:
    applicants, opened_at = parse_listing_meta(
        "Promovida · Anunciada há 2 semanas · Candidatura simplificada",
        _NOW,
    )
    assert applicants == ""
    assert opened_at == "09/09/2026 10:39 (Anunciada há 2 semanas)"


def test_parse_listing_meta_keeps_early_applicant_text() -> None:
    applicants, _opened_at = parse_listing_meta(
        "São Paulo · há 1 dia · Seja um dos primeiros a se candidatar",
        _NOW,
    )
    assert applicants == "Seja um dos primeiros a se candidatar"
