from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

WORKPLACE_TO_F_WT = {
    "onsite": "1",
    "remote": "2",
    "hybrid": "3",
}

RECENCY_TO_TPR = {
    "1h": "r3600",
    "12h": "r43200",
    "24h": "r86400",
    "week": "r604800",
}

WORKPLACE_LABELS = {
    "onsite": "presencial",
    "remote": "remoto",
    "hybrid": "híbrido",
}

RECENCY_LABELS = {
    "1h": "última hora",
    "12h": "últimas 12 horas",
    "24h": "últimas 24 horas",
    "week": "última semana",
}

SEARCH_BASE_URL = "https://www.linkedin.com/jobs/search/"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Filters:
    keywords: str
    country: str
    geo_id: str
    workplace: str
    recency: str

    @property
    def workplace_label(self) -> str:
        return WORKPLACE_LABELS[self.workplace]

    @property
    def recency_label(self) -> str:
        return RECENCY_LABELS[self.recency]

    @property
    def f_wt(self) -> str:
        return WORKPLACE_TO_F_WT[self.workplace]

    @property
    def f_tpr(self) -> str:
        return RECENCY_TO_TPR[self.recency]


@dataclass(frozen=True)
class Settings:
    filters: Filters
    phone: str
    api_key: str
    cron: str
    schedule_description: str
    timezone: str
    database: Path
    storage_state: Path
    log: Path
    lock: Path
    notify_on_session_expired: bool
    root: Path


def build_search_url(filters: Filters) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "keywords": filters.keywords,
            "f_TPR": filters.f_tpr,
            "geoId": filters.geo_id,
            "f_WT": filters.f_wt,
        }
    )
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
        msg = f"workplace inválido: {workplace!r} (use remote, hybrid ou onsite)"
        raise ValueError(msg)
    if recency not in RECENCY_TO_TPR:
        msg = f"recency inválido: {recency!r} (use 1h, 12h, 24h ou week)"
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
        ),
        phone=str(raw["whatsapp"]["phone"]).replace(" ", ""),
        api_key=api_key,
        cron=schedule["cron"],
        schedule_description=schedule.get("description", ""),
        timezone=schedule.get("timezone", "America/Sao_Paulo"),
        database=_resolve(root, paths["database"]),
        storage_state=_resolve(root, paths["storage_state"]),
        log=_resolve(root, paths["log"]),
        lock=_resolve(root, paths["lock"]),
        notify_on_session_expired=bool(
            raw.get("alerts", {}).get("notify_on_session_expired", True)
        ),
        root=root,
    )


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path
