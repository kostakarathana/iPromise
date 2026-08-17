"""Typed API models for explicitly synthetic account fixtures."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SeedAccountRequest(ApiModel):
    scenario: Literal["deletion-control"] = "deletion-control"
    run_id: str = Field(min_length=8, max_length=128)
    deletion_requested_hours_ago: int = Field(default=25, gt=24, le=168)


class SeedAccountResponse(ApiModel):
    synthetic: Literal[True] = True
    time_mode: Literal["synthetic-virtual-clock"] = "synthetic-virtual-clock"
    account_id: str
    email: str
    seeded_at: datetime
    virtual_deletion_requested_at: datetime
    virtual_observation_at: datetime
    virtual_observation_age_hours: int
    stores: list[str]


class ProcessDeletionResponse(ApiModel):
    synthetic: Literal[True] = True
    time_mode: Literal["synthetic-virtual-clock"] = "synthetic-virtual-clock"
    account_id: str
    virtual_deletion_requested_at: datetime
    virtual_processed_at: datetime
    virtual_processing_elapsed_hours: float
    accepted: Literal[True] = True


class AccountStateResponse(ApiModel):
    synthetic: Literal[True] = True
    time_mode: Literal["synthetic-virtual-clock"] = "synthetic-virtual-clock"
    account_id: str
    known_fixture: bool
    profile_exists: bool | None
    analytics_profile_exists: bool | None
    virtual_deletion_requested_at: datetime | None
    virtual_processed_at: datetime | None
    virtual_observation_at: datetime | None
    virtual_observation_elapsed_hours: float | None
    inspected_at: datetime


class ResetResponse(ApiModel):
    synthetic: Literal[True] = True
    removed_fixtures: int
