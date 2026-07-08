import json
from pathlib import Path

from app.models.app_settings import AppSettings, AppSettingsUpdate
from app.runtime_paths import get_user_data_dir


SETTINGS_FILENAME = "app-settings.json"


def get_app_settings_path() -> Path:
    return get_user_data_dir() / SETTINGS_FILENAME


def get_app_settings() -> AppSettings:
    path = get_app_settings_path()
    if not path.exists():
        settings = AppSettings()
        _write_settings(path, settings)
        return settings
    return AppSettings.model_validate_json(path.read_text(encoding="utf-8"))


def save_app_settings(update: AppSettingsUpdate) -> AppSettings:
    current = get_app_settings()
    data = current.model_dump()
    for key, value in update.model_dump(exclude_unset=True).items():
        data[key] = value
    settings = AppSettings.model_validate(data)
    _write_settings(get_app_settings_path(), settings)
    return settings


def _write_settings(path: Path, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
