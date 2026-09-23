# LinkedIn Alert → WhatsApp

Monitor de vagas no LinkedIn, a cada 30 minutos. Roda no seu usuário (venv + cron), reutiliza uma sessão que você grava manualmente e avisa no WhatsApp via CallMeBot.

Para mudar filtros, telefone ou recorrência do cron, edite só o [`config.toml`](config.toml). Com `search_url` preenchida, a busca e o alerta usam essa URL completa. Os outros campos de `[filters]` não remontam a query.

Não usamos Docker neste projeto: o login interativo e o Playwright no host são mais simples para um cron pessoal.

## Avisos

- Automatizar o LinkedIn pode violar os termos de uso e restringir a conta. A sessão é sua; o script não tenta burlar CAPTCHA/2FA.
- O CallMeBot (terceiro) recebe título, empresa, local, candidatos, data estimada de abertura, link da vaga e a URL do filtro.
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

1. No WhatsApp, adicione **+34 623 80 11 90** aos contatos e envie exatamente: `I allow callmebot to send me messages`
2. Espere a resposta `API Activated... Your APIKEY is ...`. Sem resposta em 2 minutos: tente `Recover APIKey` ou de novo em 24h (o bot muda de número; o atual está em https://www.callmebot.com/blog/free-api-whatsapp-messages/)
3. Copie a API key que o bot devolver
4. `cp .env.example .env` e cole em `CALLMEBOT_APIKEY=`

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

A linha usa `systemd-inhibit` (a busca em andamento não é suspensa por inatividade), `flock` (não abre dois Playwright), `TZ=America/Sao_Paulo` e redireciona para `data/cron.log`.

O bloco do crontab também segura um inibidor de repouso desde o boot. Com ele ativo, o computador inativo não suspende sozinho, e a busca das 30 minutos continua. Fechar a tampa ainda pode suspender. No modo bateria, isso impede o descanso automático.

## Mensagem no WhatsApp

Toda notificação começa pelos filtros:

```text
*Filtros*
Palavra-chave: laravel
País: Brasil
Modalidade: qualquer
Recência: desde 22/09/2026 07:11
Salário: qualquer
https://www.linkedin.com/jobs/search-results/?currentJobId=...&f_TPR=a1790071915-

*1 vaga nova*

*1. Analista de Sistemas Sênior (PHP)*
Empresa: Locaweb
Local: Brasil
Candidatos: Mais de 100 pessoas clicaram em Candidate-se
Aberta desde: 22/09/2026 18:42 (há 16 horas)
https://www.linkedin.com/jobs/view/4468921714
```

A última linha de *Filtros* é a `search_url` inteira, com `origin`, `currentJobId` e `f_TPR`. `Candidatos` é o texto do LinkedIn, não uma contagem própria. `Aberta desde` estima o instante a partir do “há N …” da página, no fuso `America/Sao_Paulo`, e grava esse texto no banco. Se a página não mostrar o dado, a linha vai como `não informado`.

## Operação

| Sintoma | O que fazer |
|---|---|
| Não chegou WhatsApp | Veja `data/cron.log` |
| Busca sem vaga nova | O WhatsApp recebe “Não houve dados novos encontrados.” e o último registro do banco, marcado como busca anterior. O `--dry-run` só imprime isso |
| Sessão expirada | `python -m linkedin_alert.login` (skill `renew-linkedin-session`) |
| Falta vaga | Com `search_url`, edite essa URL. Sem ela, teste `recency` (`30m`, `1h`, `12h`, `24h`, `week`) antes de culpar o scraper |
| Resultado diferente do LinkedIn | A busca tem de ser a URL completa, inclusive `f_TPR=a…-`. Remontar a query troca o filtro |
| Histórico | `data/jobs.db` — copie o arquivo se quiser backup |

O mesmo `linkedin_id` não é enviado de novo. A linha nasce com `notified_at` vazio; depois do WhatsApp aceito, o campo é preenchido. Falha no CallMeBot deixa a vaga pendente. Vaga já gravada não ganha candidatos nem data numa busca seguinte.

Consultar o banco, na raiz do projeto:

```bash
sqlite3 -header -column data/jobs.db \
  "SELECT linkedin_id, title, applicants, opened_at, notified_at FROM jobs ORDER BY id DESC;"
```

Pendentes de envio: `WHERE notified_at IS NULL`. No console, `.schema jobs` lista as colunas (`applicants`, `opened_at`, `first_seen_at`, `notified_at`). Saia com `.quit`.

Cookies duram dias/semanas até um checkpoint. Sem renovação automática.

## Comandos úteis

```bash
ruff check .
ruff format .
pytest
python -m linkedin_alert.cron --print
```
