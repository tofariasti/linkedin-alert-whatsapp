---
name: renew-linkedin-session
description: Renew the LinkedIn Playwright storage_state when the session expires or a checkpoint appears. Use when login is required, storage_state.json is missing, the user sees a WhatsApp session-expired alert, or they mention renovar sessão, cookies, or python -m linkedin_alert.login.
---

# Renew LinkedIn session

Do not ask for email/password. Do not bypass CAPTCHA or 2FA.

## Steps

1. Confirm a graphical session (headed Chromium). Cron headless cannot renew cookies.
2. From the repo root, with the project venv:

```bash
source .venv/bin/activate
python -m linkedin_alert.login
```

3. The user signs in (and completes 2FA if prompted). Wait until `/feed` or cookie `li_at`.
4. Confirm `storage_state.json` exists and is gitignored.
5. Verify without WhatsApp. Do not edit `search_url` or other filters while renewing the session. Dry-run opens that URL, inserts new rows in `data/jobs.db`, and prints the alert. It does not call CallMeBot and does not set `notified_at`.

```bash
python -m linkedin_alert --dry-run
```

6. If dry-run still reports sessão expirada, the checkpoint is still up — stop and tell the user to finish it in the opened browser. Do not retry in a loop.
