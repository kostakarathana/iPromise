"""FastAPI wire API consumed by the iPromise judge console."""

from __future__ import annotations

import hmac
import hashlib
from typing import Annotated

from fastapi import (
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .github import GitHubAuthorizationError, GitHubIntegrationError, GitHubNotConfigured
from .models import (
    AuditRun,
    CreateRunRequest,
    GitHubInstallUrl,
    GitHubIntegrationStatus,
    GitHubOAuthCallbackRequest,
    GitHubOAuthStartRequest,
    GitHubRepositorySelection,
    RunStatus,
)
from .service import ACTION_LEASE_SECONDS, AuditService


def create_app(
    *, settings: Settings | None = None, service: AuditService | None = None
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_service = service or AuditService(settings=resolved_settings)
    app = FastAPI(
        title="iPromise audit agent",
        version="0.1.0",
        description=(
            "Captures one exact customer promise, executes a deterministic synthetic "
            "control, and plans bounded responses."
        ),
    )
    app.state.settings = resolved_settings
    app.state.audit_service = resolved_service

    def bearer_token(authorization: str | None) -> str:
        prefix = "Bearer "
        if not authorization or not authorization.startswith(prefix):
            return ""
        return authorization[len(prefix) :]

    def authorize_console(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        expected = resolved_settings.api_token
        if (
            expected is None
            and resolved_settings.mode in {"demonstration", "local"}
            and resolved_settings.cloud_run_revision is None
        ):
            return
        supplied = bearer_token(authorization)
        if expected is not None and hmac.compare_digest(supplied, expected):
            return
        raise HTTPException(status_code=401, detail="A valid console identity is required")

    def authorize_scheduler(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        audience = resolved_settings.google_oidc_audience
        scheduler_service_account = resolved_settings.scheduler_service_account
        supplied = bearer_token(authorization)
        if not audience or not scheduler_service_account or not supplied:
            raise HTTPException(
                status_code=401, detail="A valid Cloud Scheduler identity is required"
            )
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token

            claims = id_token.verify_oauth2_token(
                supplied,
                google_requests.Request(),
                audience,
            )
            email = claims.get("email")
            if (
                isinstance(email, str)
                and hmac.compare_digest(email, scheduler_service_account)
                and claims.get("email_verified") is True
            ):
                return
        except Exception:
            pass
        raise HTTPException(
            status_code=401, detail="A valid Cloud Scheduler identity is required"
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request validation failed",
                }
            },
        )

    @app.get("/healthz", tags=["system"])
    async def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "service": "ipromise-agent",
            "mode": resolved_settings.mode,
            "compiler": resolved_settings.compiler,
            "modelInvoked": False,
        }

    @app.post(
        "/v1/runs",
        response_model=AuditRun,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["audits"],
    )
    async def create_run(
        body: Annotated[CreateRunRequest | None, Body()] = None,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> AuditRun:
        try:
            return await resolved_service.create_run(
                body or CreateRunRequest(), idempotency_key=idempotency_key
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/v1/triggers/scheduled",
        response_model=AuditRun,
        response_model_by_alias=True,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(authorize_scheduler)],
        tags=["triggers"],
    )
    async def scheduled_run(
        job_name: Annotated[
            str | None, Header(alias="X-CloudScheduler-JobName")
        ] = None,
        schedule_time: Annotated[
            str | None, Header(alias="X-CloudScheduler-ScheduleTime")
        ] = None,
    ) -> AuditRun | JSONResponse:
        if not job_name or not schedule_time:
            raise HTTPException(
                status_code=422,
                detail="Cloud Scheduler job name and schedule time are required",
            )
        digest = hashlib.sha256(f"{job_name}|{schedule_time}".encode()).hexdigest()
        run = await resolved_service.create_run(
            CreateRunRequest(
                trigger="scheduled",
                source="cloud-scheduler",
                idempotency_key=f"scheduler:{digest}",
            )
        )
        if run.status not in {RunStatus.COMPLETE, RunStatus.FAILED_SAFE}:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=run.model_dump(mode="json", by_alias=True),
                # A retry that arrives while the durable action lease is still
                # held cannot make progress. Advertise a delay at least as long
                # as the lease so retry policies can avoid exhausting their
                # attempts before a crashed worker's claim expires.
                headers={"Retry-After": str(ACTION_LEASE_SECONDS)},
            )
        return run

    @app.get(
        "/v1/runs",
        response_model=list[AuditRun],
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["audits"],
    )
    async def list_runs(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[AuditRun]:
        return await resolved_service.list_runs(limit)

    @app.get(
        "/v1/runs/latest",
        response_model=AuditRun,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["audits"],
    )
    async def latest_run() -> AuditRun | Response:
        run = await resolved_service.latest_run()
        if run is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return run

    @app.get(
        "/v1/runs/{run_id}",
        response_model=AuditRun,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["audits"],
    )
    async def get_run(run_id: str) -> AuditRun:
        run = await resolved_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Audit run not found")
        return run

    @app.get(
        "/v1/integrations/github",
        response_model=GitHubIntegrationStatus,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_status() -> GitHubIntegrationStatus:
        return await resolved_service.github.status()

    @app.get(
        "/v1/integrations/github/install-url",
        response_model=GitHubInstallUrl,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_install_url() -> GitHubInstallUrl:
        try:
            return await resolved_service.github.install_url()
        except GitHubNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post(
        "/v1/integrations/github/oauth-url",
        response_model=GitHubInstallUrl,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_oauth_url(body: GitHubOAuthStartRequest) -> GitHubInstallUrl:
        try:
            return await resolved_service.github.oauth_url(body)
        except GitHubNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GitHubAuthorizationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/v1/integrations/github/oauth/callback",
        response_model=GitHubIntegrationStatus,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_oauth_callback(
        body: GitHubOAuthCallbackRequest,
    ) -> GitHubIntegrationStatus:
        try:
            return await resolved_service.github.complete_oauth(body)
        except GitHubNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GitHubAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except GitHubIntegrationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.put(
        "/v1/integrations/github/repository",
        response_model=GitHubIntegrationStatus,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_select_repository(
        body: GitHubRepositorySelection,
    ) -> GitHubIntegrationStatus:
        try:
            return await resolved_service.github.select_repository(body.repository_id)
        except GitHubAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.delete(
        "/v1/integrations/github",
        response_model=GitHubIntegrationStatus,
        response_model_by_alias=True,
        dependencies=[Depends(authorize_console)],
        tags=["integrations"],
    )
    async def github_disconnect() -> GitHubIntegrationStatus:
        return await resolved_service.github.disconnect()

    return app


app = create_app()
