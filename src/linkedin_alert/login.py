from __future__ import annotations

import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from linkedin_alert.config import load_settings

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.linkedin.com/login"
WAIT_MS = 180_000


def save_session(storage_state: Path) -> None:
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    print("Abrindo o LinkedIn. Faça login (incluindo 2FA, se pedir).")
    print("O script grava a sessão quando detectar que você entrou.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_function(
                """() => location.pathname.startsWith('/feed')
                    || document.cookie.includes('li_at=')""",
                timeout=WAIT_MS,
            )
        except Exception:
            browser.close()
            msg = "Tempo esgotado esperando o login. Tente de novo."
            raise SystemExit(msg) from None

        context.storage_state(path=str(storage_state))
        browser.close()

    print(f"Sessão salva em {storage_state}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    save_session(settings.storage_state)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
