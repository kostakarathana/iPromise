"""Configuration that keeps model provenance and demo boundaries explicit."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


LOCAL_FALLBACK_TOKEN = "local-synthetic-only-change-me"


@dataclass(frozen=True, slots=True)
class Settings:
    mode: str = "demonstration"
    compiler: str = "deterministic"
    demo_base_url: str = "http://127.0.0.1:8081"
    demo_token: str = LOCAL_FALLBACK_TOKEN
    api_token: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    execution_target: str = "local-process"
    cloud_run_revision: str | None = None
    console_base_url: str = "http://127.0.0.1:3000"
    github_actions_enabled: bool = False
    github_app_id: str | None = None
    github_app_slug: str | None = None
    github_app_client_id: str | None = None
    github_app_client_secret: str | None = None
    github_app_private_key: str | None = None
    github_api_url: str = "https://api.github.com"
    github_web_url: str = "https://github.com"
    state_backend: str = "memory"
    firestore_database: str = "(default)"
    google_oidc_audience: str | None = None
    scheduler_service_account: str | None = None
    verifier_backend: str = "disabled"
    cloud_build_project: str | None = None
    cloud_build_location: str = "australia-southeast1"
    cloud_build_service_account: str | None = None

    @property
    def github_configured(self) -> bool:
        return all(
            (
                self.github_app_id,
                self.github_app_slug,
                self.github_app_client_id,
                self.github_app_client_secret,
                self.github_app_private_key,
            )
        )

    @classmethod
    def from_env(cls) -> "Settings":
        github_actions_raw = os.getenv("IPROMISE_GITHUB_ACTIONS_ENABLED", "false")
        if github_actions_raw.strip().lower() not in {"true", "false"}:
            raise ValueError("IPROMISE_GITHUB_ACTIONS_ENABLED must be true or false")
        private_key = os.getenv("IPROMISE_GITHUB_APP_PRIVATE_KEY") or None
        if private_key:
            private_key = private_key.replace("\\n", "\n")
        settings = cls(
            mode=os.getenv("IPROMISE_MODE", "demonstration").strip().lower(),
            compiler=os.getenv("IPROMISE_COMPILER", "deterministic").strip().lower(),
            demo_base_url=os.getenv(
                "IPROMISE_DEMO_BASE_URL", "http://127.0.0.1:8081"
            ).rstrip("/"),
            demo_token=os.getenv(
                "IPROMISE_DEMO_TOKEN", LOCAL_FALLBACK_TOKEN
            ),
            api_token=os.getenv("IPROMISE_AGENT_API_TOKEN") or None,
            gemini_model=os.getenv("IPROMISE_GEMINI_MODEL", "gemini-3.5-flash"),
            execution_target=os.getenv(
                "IPROMISE_EXECUTION_TARGET", "cloud-run" if os.getenv("K_REVISION") else "local-process"
            ),
            cloud_run_revision=os.getenv("K_REVISION") or None,
            console_base_url=os.getenv(
                "IPROMISE_CONSOLE_BASE_URL", "http://127.0.0.1:3000"
            ).rstrip("/"),
            github_actions_enabled=github_actions_raw.strip().lower() == "true",
            github_app_id=os.getenv("IPROMISE_GITHUB_APP_ID") or None,
            github_app_slug=os.getenv("IPROMISE_GITHUB_APP_SLUG") or None,
            github_app_client_id=os.getenv("IPROMISE_GITHUB_APP_CLIENT_ID") or None,
            github_app_client_secret=os.getenv("IPROMISE_GITHUB_APP_CLIENT_SECRET") or None,
            github_app_private_key=private_key,
            github_api_url=os.getenv(
                "IPROMISE_GITHUB_API_URL", "https://api.github.com"
            ).rstrip("/"),
            github_web_url=os.getenv(
                "IPROMISE_GITHUB_WEB_URL", "https://github.com"
            ).rstrip("/"),
            state_backend=os.getenv(
                "IPROMISE_STATE_BACKEND",
                "firestore" if os.getenv("K_REVISION") else "memory",
            ).strip().lower(),
            firestore_database=os.getenv(
                "IPROMISE_FIRESTORE_DATABASE", "(default)"
            ).strip(),
            google_oidc_audience=os.getenv("IPROMISE_GOOGLE_OIDC_AUDIENCE") or None,
            scheduler_service_account=os.getenv(
                "IPROMISE_SCHEDULER_SERVICE_ACCOUNT"
            )
            or None,
            verifier_backend=os.getenv(
                "IPROMISE_VERIFIER_BACKEND", "disabled"
            ).strip().lower(),
            cloud_build_project=os.getenv("IPROMISE_CLOUD_BUILD_PROJECT") or None,
            cloud_build_location=os.getenv(
                "IPROMISE_CLOUD_BUILD_LOCATION", "australia-southeast1"
            ).strip(),
            cloud_build_service_account=os.getenv(
                "IPROMISE_CLOUD_BUILD_SERVICE_ACCOUNT"
            )
            or None,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.mode not in {"cloud", "local", "demonstration"}:
            raise ValueError("IPROMISE_MODE must be cloud, local, or demonstration")
        if self.cloud_run_revision is not None and self.mode != "cloud":
            raise ValueError("Cloud Run requires IPROMISE_MODE=cloud")
        if self.compiler not in {"adk", "deterministic"}:
            raise ValueError("IPROMISE_COMPILER must be adk or deterministic")
        if self.compiler == "deterministic" and self.mode != "demonstration":
            raise ValueError(
                "The deterministic compiler is allowed only in explicit demonstration mode"
            )
        if self.mode == "cloud" and self.compiler != "adk":
            raise ValueError("Cloud mode requires the Google ADK compiler")
        parsed = urlparse(self.demo_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("IPROMISE_DEMO_BASE_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("IPROMISE_DEMO_BASE_URL cannot include credentials, query, or fragment")
        if self.mode == "cloud" and parsed.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Cloud mode requires a non-loopback demo service URL")
        if not self.demo_token:
            raise ValueError("IPROMISE_DEMO_TOKEN must not be empty")
        if self.mode == "cloud" and (
            self.demo_token == LOCAL_FALLBACK_TOKEN or len(self.demo_token) < 24
        ):
            raise ValueError(
                "Cloud mode requires a non-default demo token of at least 24 characters"
            )
        github_fields = (
            self.github_app_id,
            self.github_app_slug,
            self.github_app_client_id,
            self.github_app_client_secret,
            self.github_app_private_key,
        )
        console_url = urlparse(self.console_base_url)
        if console_url.scheme not in {"http", "https"} or not console_url.hostname:
            raise ValueError(
                "IPROMISE_CONSOLE_BASE_URL must be an absolute HTTP(S) origin"
            )
        if (
            console_url.username
            or console_url.password
            or console_url.query
            or console_url.fragment
            or console_url.path not in {"", "/"}
        ):
            raise ValueError(
                "IPROMISE_CONSOLE_BASE_URL must be an origin without credentials, "
                "path, query, or fragment"
            )
        if self.mode == "cloud" and any(github_fields) and console_url.scheme != "https":
            raise ValueError("Cloud mode requires an HTTPS console origin")
        for name, value in {
            "IPROMISE_GITHUB_API_URL": self.github_api_url,
            "IPROMISE_GITHUB_WEB_URL": self.github_web_url,
        }.items():
            parsed_value = urlparse(value)
            if parsed_value.scheme not in {"http", "https"} or not parsed_value.hostname:
                raise ValueError(f"{name} must be an absolute HTTP(S) URL")
        if any(github_fields) and not all(github_fields):
            raise ValueError(
                "GitHub App configuration is incomplete; app ID, slug, client ID, "
                "client secret, and private key are all required"
            )
        if self.github_actions_enabled and not self.github_configured:
            raise ValueError(
                "GitHub actions cannot be enabled until the GitHub App is fully configured"
            )
        if self.state_backend not in {"memory", "firestore"}:
            raise ValueError("IPROMISE_STATE_BACKEND must be memory or firestore")
        if self.mode == "cloud" and self.state_backend != "firestore":
            raise ValueError("Cloud mode requires Firestore-backed durable run state")
        if self.mode == "cloud" and (
            self.api_token is None or len(self.api_token) < 24
        ):
            raise ValueError(
                "Cloud mode requires an agent API bearer token of at least 24 characters"
            )
        if bool(self.google_oidc_audience) != bool(self.scheduler_service_account):
            raise ValueError(
                "Scheduler OIDC audience and service account must be configured together"
            )
        if self.verifier_backend not in {"disabled", "cloud-build"}:
            raise ValueError(
                "IPROMISE_VERIFIER_BACKEND must be disabled or cloud-build"
            )
        if self.verifier_backend == "cloud-build":
            if not self.cloud_build_project or not self.cloud_build_service_account:
                raise ValueError(
                    "Cloud Build verification requires IPROMISE_CLOUD_BUILD_PROJECT "
                    "and IPROMISE_CLOUD_BUILD_SERVICE_ACCOUNT"
                )
            from .cloudbuild_verifier import (
                CloudBuildVerifierConfig,
                VerifierConfigurationError,
            )

            try:
                CloudBuildVerifierConfig(
                    project_id=self.cloud_build_project,
                    location=self.cloud_build_location,
                    service_account=self.cloud_build_service_account,
                )
            except VerifierConfigurationError as exc:
                raise ValueError(
                    f"Invalid Cloud Build verifier configuration: {exc}"
                ) from exc
