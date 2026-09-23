# AGENTS

Monitor local de vagas LinkedIn → WhatsApp (CallMeBot). Pacote `linkedin_alert` em `src/`.

## Onde mudar o quê

- Filtros, telefone, cron, paths, alerta de sessão: **somente** [`config.toml`](config.toml)
- Segredo: `.env` (`CALLMEBOT_APIKEY`). Nunca commitar.
- Sessão LinkedIn: `storage_state.json` via `python -m linkedin_alert.login`

## Comandos

```bash
pip install -e ".[dev]"
playwright install chromium
python -m linkedin_alert --dry-run
python -m linkedin_alert.login
python -m linkedin_alert
python -m linkedin_alert.cron --print
ruff check . && pytest
```

## Convenções

- src-layout, type hints, `logging` (não `print`, exceto no login headed)
- Sem login por senha, sem bypass de CAPTCHA/2FA
- Conventional Commits, um concern por commit
- Nunca commitar `.env`, `storage_state.json`, `data/jobs.db`, `data/cron.log`

Rules: `.cursor/rules/`. Skill de sessão: `.cursor/skills/renew-linkedin-session/`.
