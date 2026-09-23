# AGENTS

Monitor local de vagas LinkedIn → WhatsApp (CallMeBot). Pacote `linkedin_alert` em `src/`.

## Onde mudar o quê

- Filtros, telefone, cron, paths, alerta de sessão: **somente** [`config.toml`](config.toml)
- `search_url` preenchida é a URL da busca e do WhatsApp, sem remontar a query. Não descartar `origin`, `currentJobId` nem `f_TPR=a…-`
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

## Busca e alerta

- Sem `search_url`, a query sai de `keywords`, `geo_id`, `workplace`, `recency` e `salary`
- `workplace = any` ou vazio em `salary` omite `f_WT` / `f_SAL`
- Recência relativa: `1h` → `f_TPR=r3600`, `12h` → `r43200`, `24h` → `r86400`, `week` → `r604800`
- O alerta manda a URL do filtro, candidatos e “aberta desde”. A data é estimada do “há N …” do LinkedIn, em `America/Sao_Paulo`
- SQLite `data/jobs.db`: uma linha por `linkedin_id`. WhatsApp só sai com `notified_at` vazio; depois do envio o campo é preenchido. `INSERT OR IGNORE` não atualiza vaga já vista

## Convenções

- src-layout, type hints, `logging` (não `print`, exceto no login headed)
- Sem login por senha, sem bypass de CAPTCHA/2FA
- Conventional Commits, um concern por commit
- Nunca commitar `.env`, `storage_state.json`, `data/jobs.db`, `data/cron.log`

Rules: `.cursor/rules/` (`python`, `filters`, `secrets`, `commits`). Skill de sessão: `.cursor/skills/renew-linkedin-session/`.
