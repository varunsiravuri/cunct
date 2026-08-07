from __future__ import annotations

import json
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from churn_autopsy.config import Settings, get_settings


class HydraClient:
    """Thin v2 HTTP client so we stay compatible even if SDK field names drift."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.api_key:
            raise RuntimeError(
                "HYDRA_DB_API_KEY is missing. Copy .env.example → .env and add your key."
            )
        self._http = httpx.Client(
            base_url=self.settings.base_url,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "API-Version": "2",
            },
            timeout=120.0,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "HydraClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(4), reraise=True)
    def ensure_database(self) -> dict[str, Any]:
        # Prefer create; tolerate already-exists.
        r = self._http.post(
            "/databases",
            json={"database": self.settings.database},
        )
        if r.status_code in (200, 201, 409):
            self.wait_database_ready()
            return r.json() if r.content else {"database": self.settings.database}
        # Some deployments use /tenants/create still.
        r2 = self._http.post(
            "/tenants/create",
            json={"tenant_id": self.settings.database},
        )
        if r2.status_code in (200, 201, 409):
            self.wait_database_ready()
            return r2.json() if r2.content else {"database": self.settings.database}
        r.raise_for_status()
        return {}

    def wait_database_ready(self, timeout_s: float = 90.0) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            for path in (
                f"/databases/status?database={self.settings.database}",
                f"/tenants/infra/status?tenant_id={self.settings.database}",
            ):
                try:
                    r = self._http.get(path)
                    if r.status_code == 200:
                        body = r.json()
                        status = (
                            body.get("status")
                            or body.get("infra_status")
                            or body.get("state")
                            or ""
                        ).lower()
                        if status in {"ready", "active", "healthy", "ok", "succeeded", "success"}:
                            return
                        if "ready" in json.dumps(body).lower():
                            return
                except httpx.HTTPError:
                    continue
            time.sleep(2)

    def ingest_app_knowledge(self, items: list[dict[str, Any]], upsert: bool = True) -> dict[str, Any]:
        # Batch limit: 20 sources per request.
        last: dict[str, Any] = {}
        for i in range(0, len(items), 20):
            batch = items[i : i + 20]
            files = {
                "type": (None, "knowledge"),
                "database": (None, self.settings.database),
                "collection": (None, self.settings.collection),
                "upsert": (None, "true" if upsert else "false"),
                "app_knowledge": (None, json.dumps(batch)),
            }
            r = self._http.post("/context/ingest", files=files)
            r.raise_for_status()
            last = r.json()
            time.sleep(1.05)
        return last

    def ingest_documents(
        self,
        documents: list[tuple[str, bytes, str]],
        document_metadata: list[dict[str, Any]],
        upsert: bool = True,
    ) -> dict[str, Any]:
        files: list[tuple[str, Any]] = [
            ("type", (None, "knowledge")),
            ("database", (None, self.settings.database)),
            ("collection", (None, self.settings.collection)),
            ("upsert", (None, "true" if upsert else "false")),
            ("document_metadata", (None, json.dumps(document_metadata))),
        ]
        for filename, content, content_type in documents:
            files.append(("documents", (filename, content, content_type)))
        r = self._http.post("/context/ingest", files=files)
        r.raise_for_status()
        return r.json()

    def wait_ingest(self, source_ids: list[str] | None = None, timeout_s: float = 120.0) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            params: dict[str, Any] = {"database": self.settings.database}
            if source_ids:
                params["ids"] = ",".join(source_ids)
            r = self._http.get("/context/status", params=params)
            if r.status_code == 200:
                body = r.json()
                blob = json.dumps(body).lower()
                if "pending" not in blob and "processing" not in blob and "queued" not in blob:
                    return
                statuses = body.get("sources") or body.get("items") or []
                if statuses and all(
                    str(s.get("status", "")).lower() in {"ready", "completed", "success", "done"}
                    for s in statuses
                ):
                    return
            time.sleep(2)

    def query(
        self,
        query: str,
        *,
        mode: str = "fast",
        metadata_filters: dict[str, Any] | None = None,
        max_results: int = 8,
        graph_context: bool = True,
        query_apps: bool = True,
        additional_context: str | None = None,
        recency_bias: float = 0.3,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "database": self.settings.database,
            "collection": self.settings.collection,
            "query": query,
            "type": "knowledge",
            "query_by": "hybrid",
            "mode": mode,
            "max_results": max_results,
            "alpha": "auto",
            "recency_bias": recency_bias,
            "graph_context": graph_context,
            "query_apps": True if query_apps else False,
        }
        if metadata_filters:
            payload["metadata_filters"] = metadata_filters
        if additional_context:
            payload["additional_context"] = additional_context
        if mode == "thinking":
            payload["query_forceful_relations"] = True

        started = time.perf_counter()
        r = self._http.post("/query", json=payload)
        latency_ms = (time.perf_counter() - started) * 1000
        r.raise_for_status()
        body = r.json()
        body["_meta"] = {
            "latency_ms": latency_ms,
            "mode": mode,
            "query": query,
            "metadata_filters": metadata_filters or {},
        }
        return body

    def create_connector(self, provider: str, name: str, credentials: dict[str, Any], **extra: Any) -> dict[str, Any]:
        payload = {
            "provider": provider,
            "name": name,
            "database": self.settings.database,
            "collection": self.settings.collection,
            "credentials": credentials,
            **extra,
        }
        r = self._http.post("/connectors", json=payload)
        r.raise_for_status()
        return r.json()

    def sync_connector(self, connector_id: str) -> dict[str, Any]:
        r = self._http.post(f"/connectors/{connector_id}/sync")
        r.raise_for_status()
        return r.json()
