from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from churn_autopsy.config import Settings, get_settings
from churn_autopsy.hydra_client import HydraClient


class HydraConnectorManager:
    """Create and configure HydraDB native connectors for Stripe, Intercom, and PostHog.

    This is intentionally separate from the manual app_knowledge ingestion path so the
    project can demonstrate both: native HydraDB connectors for production-grade DX,
    and direct app_knowledge ingestion for reproducible fixture-driven demos.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = HydraClient(self.settings)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "HydraConnectorManager":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_providers(self) -> list[dict[str, Any]]:
        r = self.client._http.get("/connectors/providers")
        r.raise_for_status()
        return r.json().get("providers", [])

    def get_provider(self, provider: str) -> dict[str, Any]:
        r = self.client._http.get("/connectors/providers", params={"id": provider})
        r.raise_for_status()
        return r.json()

    def _fetch_stripe_account_id(self) -> str | None:
        if not self.settings.stripe_api_key:
            return None
        try:
            with httpx.Client(
                base_url="https://api.stripe.com/v1",
                headers={"Authorization": f"Bearer {self.settings.stripe_api_key}"},
                timeout=30.0,
            ) as c:
                r = c.get("/account")
                r.raise_for_status()
                return r.json().get("id")
        except Exception:
            return None

    def create_connector(
        self,
        provider: str,
        name: str,
        credentials: dict[str, str],
        provider_account_scope: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": provider,
            "name": name,
            "database": self.settings.database,
            "collection": self.settings.collection,
            "credentials": credentials,
        }
        if provider_account_scope:
            payload["provider_account_scope"] = provider_account_scope
        r = self.client._http.post("/connectors", json=payload)
        # tolerate already-exists by re-reading existing connectors
        if r.status_code == 409:
            list_r = self.client._http.get(
                "/connectors",
                params={"database": self.settings.database, "provider": provider},
            )
            list_r.raise_for_status()
            for conn in list_r.json().get("connectors", []):
                if conn.get("name") == name:
                    return conn
            raise RuntimeError(f"Connector conflict but no existing {name} found")
        r.raise_for_status()
        return r.json()

    def configure_connector(self, connector_id: str, resources: list[dict[str, Any]], lookback_days: int = 30) -> dict[str, Any]:
        payload = {"lookback_days": lookback_days, "resources": resources}
        r = self.client._http.post(f"/connectors/{connector_id}/configure", json=payload)
        r.raise_for_status()
        return r.json()

    def sync_connector(self, connector_id: str) -> dict[str, Any]:
        r = self.client._http.post(f"/connectors/{connector_id}/sync")
        r.raise_for_status()
        return r.json()

    def get_connector_status(self, connector_id: str) -> dict[str, Any]:
        r = self.client._http.get(f"/connectors/{connector_id}")
        r.raise_for_status()
        return r.json()

    def setup_stripe(self) -> dict[str, Any] | None:
        if not self.settings.stripe_api_key:
            return None
        account_id = self._fetch_stripe_account_id()
        if not account_id:
            return None
        connector = self.create_connector(
            provider="stripe",
            name="cunct-stripe",
            credentials={"account_id": account_id, "client_secret": self.settings.stripe_api_key},
            provider_account_scope=account_id,
        )
        connector_id = connector.get("id") or connector.get("connector_id")
        self.configure_connector(
            connector_id,
            resources=[
                {
                    "resource_id": "customers",
                    "resource_type": "stream",
                    "name": "customers",
                    "additional_metadata": {"source": "stripe", "live": "true"},
                },
                {
                    "resource_id": "subscriptions",
                    "resource_type": "stream",
                    "name": "subscriptions",
                    "additional_metadata": {"source": "stripe", "live": "true"},
                },
                {
                    "resource_id": "refunds",
                    "resource_type": "stream",
                    "name": "refunds",
                    "additional_metadata": {"source": "stripe", "live": "true"},
                },
            ],
            lookback_days=90,
        )
        return connector

    def setup_intercom(self) -> dict[str, Any] | None:
        if not self.settings.intercom_token:
            return None
        connector = self.create_connector(
            provider="intercom",
            name="cunct-intercom",
            credentials={"access_token": self.settings.intercom_token},
            provider_account_scope="cunct-intercom-workspace",
        )
        connector_id = connector.get("id") or connector.get("connector_id")
        self.configure_connector(
            connector_id,
            resources=[
                {
                    "resource_id": "conversations",
                    "resource_type": "stream",
                    "name": "conversations",
                    "additional_metadata": {"source": "intercom", "live": "true"},
                }
            ],
            lookback_days=90,
        )
        return connector

    def setup_posthog(self) -> dict[str, Any] | None:
        if not self.settings.posthog_api_key or not self.settings.posthog_project_id:
            return None
        connector = self.create_connector(
            provider="posthog",
            name="cunct-posthog",
            credentials={
                "api_key": self.settings.posthog_api_key,
                "project_id": str(self.settings.posthog_project_id),
            },
            provider_account_scope=f"cunct-posthog-{self.settings.posthog_project_id}",
        )
        connector_id = connector.get("id") or connector.get("connector_id")
        self.configure_connector(
            connector_id,
            resources=[
                {
                    "resource_id": "persons",
                    "resource_type": "stream",
                    "name": "persons",
                    "additional_metadata": {"source": "posthog", "live": "true"},
                }
            ],
            lookback_days=90,
        )
        return connector

    def setup_all(self) -> dict[str, Any]:
        """Create, configure, and sync all connectors that have credentials."""
        results: dict[str, Any] = {}
        for name, fn in (
            ("stripe", self.setup_stripe),
            ("intercom", self.setup_intercom),
            ("posthog", self.setup_posthog),
        ):
            try:
                connector = fn()
                if not connector:
                    results[name] = {"status": "skipped", "reason": "missing credentials"}
                    continue
                connector_id = connector.get("id") or connector.get("connector_id")
                sync = self.sync_connector(connector_id)
                results[name] = {
                    "status": "created_and_synced",
                    "connector_id": connector_id,
                    "connector": connector,
                    "sync": sync,
                }
            except Exception as exc:  # noqa: BLE001
                results[name] = {"status": "error", "error": str(exc)}
        return results
