"""Validated public JSON models for relay API v1."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from relay.credentials import CREDENTIAL_MAX_LENGTH


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class HostRegistration(StrictModel):
    host_id: UUID
    display_name: str = Field(strict=True, min_length=1, max_length=120)
    platform: str = Field(strict=True, min_length=1, max_length=32)
    app_version: str | None = Field(default=None, strict=True, max_length=64)
    credential: str = Field(strict=True, max_length=CREDENTIAL_MAX_LENGTH)

    @field_validator("display_name", "platform")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not contain only whitespace")
        return value


class QuotaReport(StrictModel):
    schema_version: int = Field(strict=True)
    sampled_at: datetime
    five_hour_used: float | None = Field(
        default=None, strict=True, ge=0, le=100
    )
    five_hour_reset_at: datetime | None = None
    weekly_used: float | None = Field(
        default=None, strict=True, ge=0, le=100
    )
    weekly_reset_at: datetime | None = None
    plan_type: str | None = Field(default=None, strict=True, max_length=64)
    reset_credits_available: int | None = Field(
        default=None, strict=True, ge=0
    )
    credits_balance: float | None = Field(default=None, strict=True, ge=0)
    spend_control_reached: bool | None = Field(default=None, strict=True)
    rate_limit_reached_type: str | None = Field(
        default=None, strict=True, max_length=64
    )
    collector_state: Literal["ok", "degraded", "error"] = "ok"
    collector_message_code: str | None = Field(
        default=None, strict=True, max_length=128
    )

    @field_validator("schema_version")
    @classmethod
    def require_schema_version_one(cls, value: int) -> int:
        if value != 1:
            raise ValueError("schema_version must be 1")
        return value

    @field_validator("sampled_at", "five_hour_reset_at", "weekly_reset_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value
