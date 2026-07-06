from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["low", "medium", "high"]
AuditResult = Literal["success", "denied", "error"]


class PermissionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    description: str = Field(min_length=1)
    risk_level: RiskLevel


class RoleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    permission_codes: list[str] = Field(min_length=1)


class UserItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    role_ids: list[str] = Field(min_length=1)
    active: bool


class PermissionListResponse(BaseModel):
    permissions: list[PermissionItem]


class RoleListResponse(BaseModel):
    roles: list[RoleItem]


class UserListResponse(BaseModel):
    users: list[UserItem]


class AuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    permission_code: str = Field(min_length=1)


class AuthorizationDecision(BaseModel):
    allowed: bool
    user_id: str
    permission_code: str
    matched_role_ids: list[str] = []
    reason: str


class AuditLogCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    result: AuditResult
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    actor_id: str
    module_id: str
    event: str
    target_id: str
    result: AuditResult
    metadata: dict[str, str | int | float | bool | None]
    created_at: str


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogEntry]
