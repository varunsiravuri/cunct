from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    database: str
    collection: str
    stripe_api_key: str | None
    intercom_token: str | None
    posthog_api_key: str | None
    posthog_project_id: str | None
    posthog_host: str
    cost_fast_usd: float
    cost_thinking_usd: float

    @property
    def has_live_connectors(self) -> bool:
        return bool(self.stripe_api_key and self.intercom_token and self.posthog_api_key)


def get_settings() -> Settings:
    api_key = os.getenv("HYDRA_DB_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        # Allow offline fixture generation / dry-run without a key.
        api_key = ""

    return Settings(
        api_key=api_key,
        base_url=os.getenv("HYDRA_DB_BASE_URL", "https://api.hydradb.com").rstrip("/"),
        database=os.getenv("HYDRA_DATABASE", "churn_autopsy"),
        collection=os.getenv("HYDRA_COLLECTION", "default"),
        stripe_api_key=os.getenv("STRIPE_API_KEY") or None,
        intercom_token=os.getenv("INTERCOM_ACCESS_TOKEN") or None,
        posthog_api_key=os.getenv("POSTHOG_API_KEY") or None,
        posthog_project_id=os.getenv("POSTHOG_PROJECT_ID") or None,
        posthog_host=os.getenv("POSTHOG_HOST", "https://us.posthog.com").rstrip("/"),
        cost_fast_usd=float(os.getenv("COST_FAST_USD", "0.001")),
        cost_thinking_usd=float(os.getenv("COST_THINKING_USD", "0.01")),
    )
