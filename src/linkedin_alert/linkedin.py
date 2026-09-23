from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from linkedin_alert.config import Settings, build_search_url
from linkedin_alert.models import Job

logger = logging.getLogger(__name__)

JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")
EXPIRED_MARKERS = ("/login", "/checkpoint", "/uas/login", "authwall")
_SAO_PAULO = ZoneInfo("America/Sao_Paulo")
_RELATIVE_RE = re.compile(
    r"há\s+(\d+)\s+(minuto|minutos|hora|horas|dia|dias|semana|semanas|m[eê]s|meses)",
    re.IGNORECASE,
)
_UNIT_SECONDS = {
    "minuto": 60,
    "minutos": 60,
    "hora": 3600,
    "horas": 3600,
    "dia": 86400,
    "dias": 86400,
    "semana": 604800,
    "semanas": 604800,
    "mes": 2_592_000,
    "meses": 2_592_000,
}

LISTING_READY_JS = """
() => [...document.querySelectorAll("p, span")].some((node) => {
  const text = (node.innerText || "").replace(/\\s+/g, " ").trim();
  return text.length > 0 && text.length <= 180 && text.includes("·")
    && /há\\s+\\d+/i.test(text);
})
"""

LISTING_TEXT_JS = """
() => {
  let best = "";
  for (const node of document.querySelectorAll("p, span")) {
    const text = (node.innerText || "").replace(/\\s+/g, " ").trim();
    if (!text || text.length > 180 || !text.includes("·")) continue;
    if (!/há\\s+\\d+/i.test(text)) continue;
    if (!best || text.length < best.length) best = text;
  }
  return best;
}
"""

EXTRACT_JOBS_JS = """
() => {
  const seen = new Set();
  const jobs = [];
  for (const anchor of document.querySelectorAll('a[href*="/jobs/view/"]')) {
    const href = anchor.href || "";
    const match = href.match(/\\/jobs\\/view\\/(\\d+)/);
    if (!match || seen.has(match[1])) {
      continue;
    }
    seen.add(match[1]);
    const card = anchor.closest(
      "li, .job-card-container, .scaffold-layout__list-item, .job-card-list"
    );
    const title = (
      anchor.innerText ||
      anchor.getAttribute("aria-label") ||
      ""
    ).trim().split("\\n")[0];
    const companyEl = card && card.querySelector(
      [
        ".artdeco-entity-lockup__subtitle",
        ".job-card-container__primary-description",
        ".base-search-card__subtitle",
      ].join(", ")
    );
    const locationEl = card && card.querySelector(
      [
        ".job-card-container__metadata-item",
        ".job-search-card__location",
        ".artdeco-entity-lockup__caption",
      ].join(", ")
    );
    jobs.push({
      id: match[1],
      title: title || "Vaga sem título",
      company: companyEl ? companyEl.innerText.trim().split("\\n")[0] : "",
      location: locationEl ? locationEl.innerText.trim().split("\\n")[0] : "",
      url: `https://www.linkedin.com/jobs/view/${match[1]}`,
    });
  }
  return jobs;
}
"""


class SessionExpiredError(Exception):
    """LinkedIn redirected to login or a checkpoint."""


def scrape_jobs(settings: Settings) -> list[Job]:
    if not settings.storage_state.exists():
        msg = (
            f"Sessão não encontrada em {settings.storage_state}. "
            "Rode: python -m linkedin_alert.login"
        )
        raise SessionExpiredError(msg)

    url = build_search_url(settings.filters)
    logger.info("Abrindo busca: %s", url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            return _scrape_with_browser(browser, settings.storage_state, url)
        finally:
            browser.close()


def _scrape_with_browser(browser: Browser, storage_state: Path, url: str) -> list[Job]:
    context = browser.new_context(storage_state=str(storage_state))
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)
    _assert_session(page)

    try:
        page.wait_for_selector('a[href*="/jobs/view/"]', timeout=20_000)
    except PlaywrightTimeoutError:
        logger.info("Nenhum card de vaga na primeira página")
        context.close()
        return []

    raw_jobs = page.evaluate(EXTRACT_JOBS_JS)
    jobs: list[Job] = []
    for item in raw_jobs:
        job_id = str(item.get("id") or "")
        if not JOB_ID_RE.search(f"/jobs/view/{job_id}"):
            continue
        url = item.get("url") or f"https://www.linkedin.com/jobs/view/{job_id}"
        applicants, opened_at = _listing_meta(page, url)
        jobs.append(
            Job(
                linkedin_id=job_id,
                title=(item.get("title") or "Vaga sem título").strip(),
                company=(item.get("company") or "Empresa não informada").strip(),
                location=(item.get("location") or "Local não informado").strip(),
                url=url,
                applicants=applicants,
                opened_at=opened_at,
            )
        )
    context.close()
    logger.info("Extraídas %s vagas da primeira página", len(jobs))
    return jobs


def parse_listing_meta(text: str, now: datetime) -> tuple[str, str]:
    """Applicants phrase and an estimated open date from the LinkedIn header."""
    applicants = ""
    posted = ""
    for part in (piece.strip() for piece in text.split("·")):
        if not part:
            continue
        if not posted and _RELATIVE_RE.search(part):
            posted = part
        elif _is_applicant_text(part):
            applicants = part
    if not posted:
        return applicants, ""
    opened = _opened_label(posted, now)
    return applicants, opened or posted


def _listing_meta(page: Page, url: str) -> tuple[str, str]:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    _assert_session(page)
    try:
        page.wait_for_function(LISTING_READY_JS, timeout=12_000)
    except PlaywrightTimeoutError:
        logger.info("Vaga sem data ou candidaturas: %s", url)
        return "", ""
    text = page.evaluate(LISTING_TEXT_JS)
    return parse_listing_meta(text or "", datetime.now(_SAO_PAULO))


def _is_applicant_text(part: str) -> bool:
    low = part.casefold()
    if "candidatura simplificada" in low or low.startswith("avaliando"):
        return False
    if "primeir" in low and "candidat" in low:
        return True
    if not re.search(r"\d", part):
        return False
    return any(
        token in low
        for token in ("candidat", "applicant", "pessoas clicaram", "clicked apply")
    )


def _opened_label(posted: str, now: datetime) -> str:
    match = _RELATIVE_RE.search(posted)
    if not match:
        return posted
    amount = int(match.group(1))
    unit = match.group(2).casefold().replace("ê", "e")
    seconds = _UNIT_SECONDS.get(unit)
    if seconds is None:
        return posted
    moment = now.astimezone(_SAO_PAULO) - timedelta(seconds=amount * seconds)
    stamp = moment.strftime("%d/%m/%Y %H:%M")
    return f"{stamp} ({posted})"


def _assert_session(page: Page) -> None:
    current = page.url.lower()
    if any(marker in current for marker in EXPIRED_MARKERS):
        msg = f"Sessão expirada ou checkpoint (url={page.url})"
        raise SessionExpiredError(msg)
