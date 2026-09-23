from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from linkedin_alert.config import Settings, build_search_url
from linkedin_alert.models import Job

logger = logging.getLogger(__name__)

JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")
EXPIRED_MARKERS = ("/login", "/checkpoint", "/uas/login", "authwall")

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
    context.close()

    jobs: list[Job] = []
    for item in raw_jobs:
        job_id = str(item.get("id") or "")
        if not JOB_ID_RE.search(f"/jobs/view/{job_id}"):
            continue
        jobs.append(
            Job(
                linkedin_id=job_id,
                title=(item.get("title") or "Vaga sem título").strip(),
                company=(item.get("company") or "Empresa não informada").strip(),
                location=(item.get("location") or "Local não informado").strip(),
                url=item.get("url") or f"https://www.linkedin.com/jobs/view/{job_id}",
            )
        )
    logger.info("Extraídas %s vagas da primeira página", len(jobs))
    return jobs


def _assert_session(page: Page) -> None:
    current = page.url.lower()
    if any(marker in current for marker in EXPIRED_MARKERS):
        msg = f"Sessão expirada ou checkpoint (url={page.url})"
        raise SessionExpiredError(msg)
