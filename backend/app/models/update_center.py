from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


UpdateResultStatus = Literal["updated", "up_to_date", "not_configured", "failed"]


class UpdateCenterConfig(BaseModel):
    provider: str = "codex"
    auto_update_enabled: bool = True
    schedule_day: int = Field(default=1, ge=1, le=28)
    update_channel: str = "stable"
    manifest_url: str = ""
    app_manifest_url: str = ""
    proxy_url: str | None = None


class UpdateCenterEvent(BaseModel):
    event: str
    status: UpdateResultStatus | Literal["scheduled"]
    message: str
    created_at: datetime


class UpdateCenterStatus(BaseModel):
    config: UpdateCenterConfig = Field(default_factory=UpdateCenterConfig)
    online_status: Literal["not_configured", "online", "failed", "offline"] = "not_configured"
    current_app_version: str = "0.1.0"
    available_app_version: str | None = None
    app_update_package_path: str | None = None
    app_update_required: bool = False
    current_policy_version: str = "local-bundled"
    current_policy_package_path: str | None = None
    last_checked_at: datetime | None = None
    last_successful_update_at: datetime | None = None
    last_scheduled_check_at: datetime | None = None
    last_scheduled_check_month: str | None = None
    next_scheduled_check: datetime | None = None
    last_error: str | None = None
    events: list[UpdateCenterEvent] = Field(default_factory=list)


class PolicyPackageManifest(BaseModel):
    version: str
    published_at: datetime
    package_url: HttpUrl
    sha256: str = Field(min_length=64, max_length=64)
    summary: str


class ApplicationUpdateManifest(BaseModel):
    version: str
    published_at: datetime
    package_url: HttpUrl
    sha256: str = Field(min_length=64, max_length=64)
    summary: str
    mandatory: bool = False


class UpdateCheckResult(BaseModel):
    status: UpdateResultStatus
    message: str
    current_policy_version: str
    checked_at: datetime
    manifest_version: str | None = None


class ApplicationUpdateCheckResult(BaseModel):
    status: UpdateResultStatus
    message: str
    current_app_version: str
    checked_at: datetime
    available_app_version: str | None = None
    update_package_path: str | None = None
    mandatory: bool = False
