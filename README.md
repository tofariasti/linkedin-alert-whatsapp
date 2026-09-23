# LinkedIn Alert → WhatsApp

Monitor horário de vagas **Laravel remotas no Brasil**. Roda no seu usuário (venv + cron), reutiliza uma sessão do LinkedIn que você grava manualmente e avisa no WhatsApp via CallMeBot.

Para mudar filtros, telefone ou recorrência do cron, edite só o [`config.toml`](config.toml).

Não usamos Docker neste projeto: o login interativo e o Playwright no host são mais simples para um cron pessoal.

## Avisos

- Automatizar o LinkedIn pode violar os termos de uso e restringir a conta. A sessão é sua; o script não tenta burlar CAPTCHA/2FA.
- O CallMeBot (terceiro) recebe título, empresa e link das vagas.
- O número no `config.toml` só é aceitável porque este repositório é **privado**.
- Nunca commite `.env`, `storage_state.json` ou `data/`.

## Pré-requisitos

- Python 3.11+
- Linux com `cron` e `flock`
- Conta LinkedIn
- WhatsApp no número configurado

## Setup (nessa ordem)

### 1. Ambiente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

Se `python3 -m venv` falhar (Debian/Ubuntu sem `python3-venv`):

```bash
uv venv .venv --python python3
uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/playwright install chromium
```

### 2. CallMeBot

1. No WhatsApp, adicione **+34 644 51 97 23** e envie: `I allow callmebot to send me messages`
2. Copie a API key que o bot devolver
3. `cp .env.example .env` e cole em `CALLMEBOT_APIKEY=`

### 3. Dry-run (sem sessão)

```bash
python -m linkedin_alert --dry-run
```

Sem `storage_state.json` o comando falha de propósito. Isso confirma que o pacote carrega o `config.toml`.

### 4. Login manual (sessão gráfica)

```bash
python -m linkedin_alert.login
```

Faça login (e 2FA, se pedir). O script grava `storage_state.json` (gitignored).

### 5. Dry-run de verdade

```bash
python -m linkedin_alert --dry-run
```

A 1ª execução grava as vagas no SQLite e imprime o lote. A 2ª não lista as mesmas como novas no banco.

Não pule o dry-run: ele não envia WhatsApp e não marca `notified_at`.

### 6. Um run real

```bash
python -m linkedin_alert
```

### 7. Cron (mesmo usuário do login, nunca root)

```bash
python -m linkedin_alert.cron --print    # só mostra a linha
python -m linkedin_alert.cron --install  # grava no crontab do usuário
```

A linha usa `flock` (não abre dois Playwright), `TZ=America/Sao_Paulo` e redireciona para `data/cron.log`.

O PC precisa estar **ligado e acordado**. Cron em laptop suspenso não dispara. Alternativa futura (não implementada): timer `systemd --user` com `Persistent=true`.

## Mensagem no WhatsApp

Toda notificação começa pelos filtros:

```text
*Filtros*
Palavra-chave: laravel
País: Brasil
Modalidade: remoto
Recência: última hora

*2 vagas novas*

*1. Desenvolvedor Laravel Pleno*
Empresa: Acme Tech
Local: Brasil (Remoto)
https://www.linkedin.com/jobs/view/4469829157
```

## Operação

| Sintoma | O que fazer |
|---|---|
| Não chegou WhatsApp | Veja `data/cron.log` |
| Sessão expirada | `python -m linkedin_alert.login` (skill `renew-linkedin-session`) |
| Falta vaga | Teste `recency = "12h"` no `config.toml` antes de culpar o scraper |
| Brasil + remoto incompleto | O LinkedIn mistura “worldwide” e híbrido; o bloco Filtros deixa isso explícito |
| Histórico | `data/jobs.db` — copie o arquivo se quiser backup |

Cookies duram dias/semanas até um checkpoint. Sem renovação automática.

## Comandos úteis

```bash
ruff check .
ruff format .
pytest
python -m linkedin_alert.cron --print
```
