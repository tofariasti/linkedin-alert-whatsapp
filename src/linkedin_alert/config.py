from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

WORKPLACE_TO_F_WT = {
    "onsite": "1",
    "remote": "2",
    "hybrid": "3",
    "any": "",
}

RECENCY_TO_TPR = {
    "30m": "r1800",
    "1h": "r3600",
    "12h": "r43200",
    "24h": "r86400",
    "week": "r604800",
}

WORKPLACE_LABELS = {
    "onsite": "presencial",
    "remote": "remoto",
    "hybrid": "híbrido",
    "any": "qualquer",
}

RECENCY_LABELS = {
    "30m": "últimos 30 minutos",
    "1h": "última hora",
    "12h": "últimas 12 horas",
    "24h": "últimas 24 horas",
    "week": "última semana",
}

SEARCH_BASE_URL = "https://www.linkedin.com/jobs/search/"
_SAO_PAULO = ZoneInfo("America/Sao_Paulo")
_ABSOLUTE_TPR = re.compile(r"a(\d+)-(\d*)")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Filters:
    keywords: str
    country: str
    geo_id: str
    workplace: str
    recency: str
    salary: str = ""
    search_url: str = ""

    @property
    def keywords_label(self) -> str:
        if self.search_url:
            return _query_param(self.search_url, "keywords") or self.keywords
        return self.keywords

    @property
    def workplace_label(self) -> str:
        if self.search_url:
            wt = _query_param(self.search_url, "f_WT")
            if not wt:
                return WORKPLACE_LABELS["any"]
            for key, code in WORKPLACE_TO_F_WT.items():
                if code == wt:
                    return WORKPLACE_LABELS[key]
            return wt
        return WORKPLACE_LABELS[self.workplace]

    @property
    def recency_label(self) -> str:
        if self.search_url:
            tpr = _query_param(self.search_url, "f_TPR")
            if tpr:
                return _format_tpr_label(tpr)
        return RECENCY_LABELS[self.recency]

    @property
    def salary_label(self) -> str:
        if self.search_url:
            return _query_param(self.search_url, "f_SAL") or "qualquer"
        return self.salary or "qualquer"

    @property
    def f_wt(self) -> str:
        return WORKPLACE_TO_F_WT[self.workplace]

    @property
    def f_tpr(self) -> str:
        return RECENCY_TO_TPR[self.recency]

    @property
    def f_sal(self) -> str:
        return self.salary


@dataclass(frozen=True)
class Settings:
    filters: Filters
    phone: str
    api_key: str
    cron: tuple[str, ...]
    schedule_description: str
    timezone: str
    database: Path
    storage_state: Path
    log_dir: Path
    lock: Path
    notify_on_session_expired: bool
    root: Path


def build_search_url(filters: Filters) -> str:
    if filters.search_url:
        return filters.search_url

    params = {
        "keywords": filters.keywords,
        "f_TPR": filters.f_tpr,
        "geoId": filters.geo_id,
    }
    if filters.f_wt:
        params["f_WT"] = filters.f_wt
    if filters.f_sal:
        params["f_SAL"] = filters.f_sal
    query = urlencode(params)
    return f"{SEARCH_BASE_URL}?{query}"


def load_settings(root: Path | None = None) -> Settings:
    root = root or project_root()
    load_dotenv(root / ".env")

    config_path = root / "config.toml"
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    filters_raw = raw["filters"]
    workplace = filters_raw["workplace"]
    recency = filters_raw["recency"]
    if workplace not in WORKPLACE_TO_F_WT:
        msg = f"workplace inválido: {workplace!r} (use remote, hybrid, onsite ou any)"
        raise ValueError(msg)
    if recency not in RECENCY_TO_TPR:
        msg = f"recency inválido: {recency!r} (use 30m, 1h, 12h, 24h ou week)"
        raise ValueError(msg)

    paths = raw["paths"]
    schedule = raw["schedule"]
    api_key = os.environ.get("CALLMEBOT_APIKEY", "").strip()

    return Settings(
        filters=Filters(
            keywords=filters_raw["keywords"],
            country=filters_raw["country"],
            geo_id=str(filters_raw["geo_id"]),
            workplace=workplace,
            recency=recency,
            salary=str(filters_raw.get("salary", "")).strip(),
            search_url=_search_url(filters_raw.get("search_url", "")),
        ),
        phone=str(raw["whatsapp"]["phone"]).replace(" ", ""),
        api_key=api_key,
        cron=_cron_expressions(schedule["cron"]),
        schedule_description=schedule.get("description", ""),
        timezone=schedule.get("timezone", "America/Sao_Paulo"),
        database=_resolve(root, paths["database"]),
        storage_state=_resolve(root, paths["storage_state"]),
        log_dir=_resolve(root, paths["log_dir"]),
        lock=_resolve(root, paths["lock"]),
        notify_on_session_expired=bool(
            raw.get("alerts", {}).get("notify_on_session_expired", True)
        ),
        root=root,
    )


def _cron_expressions(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_lines = [value]
    elif isinstance(value, list):
        raw_lines = [str(item) for item in value]
    else:
        msg = "cron inválido: use uma expressão ou uma lista"
        raise ValueError(msg)
    lines = tuple(line.strip() for line in raw_lines if line.strip())
    if not lines:
        msg = "cron vazio"
        raise ValueError(msg)
    return lines


def _search_url(value: object) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if not url.startswith("https://www.linkedin.com/jobs/"):
        msg = "search_url deve começar com https://www.linkedin.com/jobs/"
        raise ValueError(msg)
    return url


def _query_param(url: str, name: str) -> str:
    values = parse_qs(urlparse(url).query).get(name, [])
    return values[0] if values else ""


def _format_tpr_label(tpr: str) -> str:
    for key, code in RECENCY_TO_TPR.items():
        if code == tpr:
            return RECENCY_LABELS[key]
    match = _ABSOLUTE_TPR.fullmatch(tpr)
    if not match:
        return tpr
    start = _format_timestamp(int(match.group(1)))
    if match.group(2):
        return f"de {start} até {_format_timestamp(int(match.group(2)))}"
    return f"desde {start}"


def _format_timestamp(epoch: int) -> str:
    moment = datetime.fromtimestamp(epoch, _SAO_PAULO)
    return moment.strftime("%d/%m/%Y %H:%M")


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path
