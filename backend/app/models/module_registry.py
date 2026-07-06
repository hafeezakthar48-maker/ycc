from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ModuleStatus = Literal["mvp", "planned"]


class OsModule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: ModuleStatus
    api_prefixes: list[str] = Field(min_length=1)
    capabilities: list[str] = Field(min_length=3)
    requires_permission: bool
    audit_events: list[str] = Field(min_length=1)
    rate_limit_policy: str = Field(min_length=1)


class ModuleRegistryResponse(BaseModel):
    modules: list[OsModule]
