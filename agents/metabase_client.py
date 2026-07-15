"""NORP Metabase API client — optional live dataset ingestion."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

from agents.base import DATA_RAW, AgentResult, save_json, setup_logger

logger = setup_logger(__name__)

NORP_RAW_DIR = DATA_RAW / "norp"


class MetabaseClient:
    """Connect to a Metabase instance and export query results as CSV."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("METABASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("METABASE_API_KEY")
        self.username = username or os.getenv("METABASE_USERNAME")
        self.password = password or os.getenv("METABASE_PASSWORD")
        self.session_id: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and (self.api_key or (self.username and self.password)))

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        if self.session_id:
            return {"X-Metabase-Session": self.session_id, "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}

    def authenticate(self) -> None:
        if self.api_key or not self.username:
            return
        resp = requests.post(
            f"{self.base_url}/api/session",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        resp.raise_for_status()
        self.session_id = resp.json().get("id")
        logger.info("Metabase session established")

    def list_databases(self) -> list[dict]:
        self.authenticate()
        resp = requests.get(f"{self.base_url}/api/database", headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data

    def run_native_query(self, database_id: int, sql: str) -> pd.DataFrame:
        self.authenticate()
        payload = {"database": database_id, "type": "native", "native": {"query": sql}}
        resp = requests.post(
            f"{self.base_url}/api/dataset",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        rows = result.get("data", {}).get("rows", [])
        cols = [c.get("name") for c in result.get("data", {}).get("cols", [])]
        return pd.DataFrame(rows, columns=cols)

    def save_dataframe(self, df: pd.DataFrame, filename: str) -> Path:
        NORP_RAW_DIR.mkdir(parents=True, exist_ok=True)
        dest = NORP_RAW_DIR / filename
        df.to_csv(dest, index=False)
        logger.info("Saved Metabase export: %s (%d rows)", dest, len(df))
        return dest


def sync_norp_datasets() -> AgentResult:
    """
    Pull configured NORP tables from Metabase into data/raw/norp/.

    Set in .env:
      METABASE_URL, METABASE_API_KEY (or USERNAME/PASSWORD)
      METABASE_DATABASE_ID=2
      NORP_METABASE_QUERIES=orgs:SELECT * FROM organizations LIMIT 10000
    """
    client = MetabaseClient()
    if not client.configured:
        return AgentResult(
            agent="metabase",
            success=False,
            message="Metabase not configured — set METABASE_URL and credentials in .env",
        )

    db_id = int(os.getenv("METABASE_DATABASE_ID", "1"))
    query_specs = os.getenv("NORP_METABASE_QUERIES", "")
    exports: list[dict] = []

    if query_specs:
        for entry in query_specs.split(";"):
            if ":" not in entry:
                continue
            name, sql = entry.split(":", 1)
            df = client.run_native_query(db_id, sql.strip())
            path = client.save_dataframe(df, f"{name.strip()}.csv")
            exports.append({"name": name.strip(), "path": str(path), "rows": len(df)})
    else:
        dbs = client.list_databases()
        save_json({"databases": dbs}, NORP_RAW_DIR / "metabase_inventory.json")
        return AgentResult(
            agent="metabase",
            success=True,
            message=f"Connected to Metabase — {len(dbs)} databases. Set NORP_METABASE_QUERIES to export.",
            data={"databases": dbs},
        )

    return AgentResult(
        agent="metabase",
        success=len(exports) > 0,
        message=f"Exported {len(exports)} NORP tables from Metabase",
        data={"exports": exports},
    )
