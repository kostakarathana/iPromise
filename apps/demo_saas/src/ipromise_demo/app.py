"""FastAPI application for the deliberately flawed synthetic SaaS."""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from .config import Settings
from .contract import DELETION_PROMISE
from .models import (
    AccountStateResponse,
    ProcessDeletionResponse,
    ResetResponse,
    SeedAccountRequest,
    SeedAccountResponse,
)
from .store import SyntheticStore


PRIVACY_HTML = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%23171714'/%3E%3Cpath d='M18 33.5 27.5 43 47 22' fill='none' stroke='white' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
    <title>Northstar · Privacy policy</title>
    <style>
      :root {{ color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; }}
      body {{ margin: 0; background: #f7f7f4; color: #171714; }}
      main {{ max-width: 720px; margin: 10vh auto; padding: 48px; background: white;
              border: 1px solid #e3e3dc; border-radius: 18px; }}
      .badge {{ display: inline-block; padding: 6px 10px; border-radius: 999px;
                background: #fff0c2; color: #5d4300; font-size: 12px; font-weight: 700; }}
      h1 {{ margin: 24px 0 12px; font-size: clamp(36px, 7vw, 64px); letter-spacing: -0.05em; }}
      p {{ font-size: 19px; line-height: 1.65; }}
      .promise {{ margin-top: 32px; padding: 24px; border-left: 4px solid #171714;
                  background: #f7f7f4; font-weight: 650; }}
      footer {{ margin-top: 40px; color: #6c6c64; font-size: 14px; }}
    </style>
  </head>
  <body>
    <main>
      <span class="badge">SYNTHETIC HACKATHON FIXTURE</span>
      <h1>Privacy, plainly.</h1>
      <p>This reference service uses fake accounts and ephemeral data only.</p>
      <p id="account-deletion" class="promise" data-ipromise-claim="account-deletion">{DELETION_PROMISE}</p>
      <footer>Last updated August 17, 2026 · Synthetic test environment</footer>
    </main>
  </body>
</html>"""


def create_app(
    *, settings: Settings | None = None, store: SyntheticStore | None = None
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_store = store or SyntheticStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.store = resolved_store
        yield

    app = FastAPI(
        title="iPromise Synthetic Reference SaaS",
        version="0.1.0",
        description=(
            "A deliberately flawed, synthetic-only service used to test iPromise. "
            "It is not a production system."
        ),
        lifespan=lifespan,
    )

    def require_demo_token(
        request: Request,
        token: Annotated[str | None, Header(alias="X-iPromise-Demo-Token")] = None,
    ) -> None:
        expected = request.app.state.settings.demo_token
        if token is None or not hmac.compare_digest(token, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid synthetic-demo token is required",
            )

    @app.get("/health", tags=["system"])
    @app.get("/healthz", tags=["system"])
    async def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "service": "ipromise-synthetic-reference",
            "synthetic": True,
        }

    @app.get("/privacy", response_class=HTMLResponse, tags=["public"])
    async def privacy() -> HTMLResponse:
        return HTMLResponse(
            PRIVACY_HTML,
            headers={
                "Cache-Control": "no-store",
                "X-iPromise-Synthetic": "true",
            },
        )

    @app.post(
        "/v1/synthetic/accounts",
        response_model=SeedAccountResponse,
        dependencies=[Depends(require_demo_token)],
        tags=["synthetic-control"],
    )
    async def seed_account(request: Request, body: SeedAccountRequest) -> SeedAccountResponse:
        return request.app.state.store.seed(
            body.run_id, body.deletion_requested_hours_ago
        )

    @app.post(
        "/v1/synthetic/accounts/{account_id}/process-deletion",
        response_model=ProcessDeletionResponse,
        dependencies=[Depends(require_demo_token)],
        tags=["synthetic-control"],
    )
    async def process_deletion(
        request: Request, account_id: str
    ) -> ProcessDeletionResponse:
        result = request.app.state.store.process_deletion(account_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Synthetic fixture not found")
        return result

    @app.get(
        "/v1/synthetic/accounts/{account_id}/state",
        response_model=AccountStateResponse,
        dependencies=[Depends(require_demo_token)],
        tags=["synthetic-control"],
    )
    async def inspect_account(request: Request, account_id: str) -> AccountStateResponse:
        return request.app.state.store.inspect(account_id)

    @app.delete(
        "/v1/synthetic/accounts",
        response_model=ResetResponse,
        dependencies=[Depends(require_demo_token)],
        tags=["synthetic-control"],
    )
    async def reset_accounts(request: Request) -> ResetResponse:
        return ResetResponse(removed_fixtures=request.app.state.store.reset())

    return app


app = create_app()
