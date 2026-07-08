from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    company_name: str = "示例制造企业"
    default_account_set_id: str = "default"
    current_period: str = "2026-06"
    onboarding_completed: bool = False
    policy_manifest_url: str | None = None
    app_manifest_url: str | None = None


class AppSettingsUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1)
    default_account_set_id: str | None = Field(default=None, min_length=1)
    current_period: str | None = Field(default=None, min_length=7, max_length=7)
    onboarding_completed: bool | None = None
    policy_manifest_url: str | None = None
    app_manifest_url: str | None = None
