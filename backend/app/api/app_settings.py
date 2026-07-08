from fastapi import APIRouter

from app.models.app_settings import AppSettings, AppSettingsUpdate
from app.services.app_settings_service import get_app_settings, save_app_settings


router = APIRouter(prefix="/api/v1/app-settings", tags=["app-settings"])


@router.get("", response_model=AppSettings)
def read_app_settings() -> AppSettings:
    return get_app_settings()


@router.put("", response_model=AppSettings)
def update_app_settings(update: AppSettingsUpdate) -> AppSettings:
    return save_app_settings(update)
