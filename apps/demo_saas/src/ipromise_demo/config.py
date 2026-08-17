"""Environment-backed configuration with safe cloud defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


LOCAL_FALLBACK_TOKEN = "local-synthetic-only-change-me"


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "local"
    demo_token: str = LOCAL_FALLBACK_TOKEN

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            environment=os.getenv(
                "IPROMISE_DEMO_ENV", "cloud" if os.getenv("K_REVISION") else "local"
            )
            .strip()
            .lower(),
            demo_token=os.getenv("IPROMISE_DEMO_TOKEN", LOCAL_FALLBACK_TOKEN),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.demo_token:
            raise ValueError("IPROMISE_DEMO_TOKEN must not be empty")
        if self.environment in {"cloud", "production"}:
            if self.demo_token == LOCAL_FALLBACK_TOKEN or len(self.demo_token) < 24:
                raise ValueError(
                    "Cloud deployments require an IPROMISE_DEMO_TOKEN of at least 24 characters"
                )
