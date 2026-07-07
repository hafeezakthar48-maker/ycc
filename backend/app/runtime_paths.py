import os
import sys
from pathlib import Path


APP_DIR_NAME = "ChinaFinanceAIAssistant"
DATA_DIR_ENV = "FINANCE_AI_DATA_DIR"
FRONTEND_DIST_ENV = "FINANCE_AI_FRONTEND_DIST"


def get_user_data_dir() -> Path:
    configured = os.environ.get(DATA_DIR_ENV)
    if configured:
        return Path(configured).expanduser()

    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA")
        if base_dir:
            return Path(base_dir) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME

    base_dir = os.environ.get("XDG_DATA_HOME")
    if base_dir:
        return Path(base_dir) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def get_default_database_path(filename: str) -> Path:
    return get_user_data_dir() / filename


def get_frontend_dist_dir() -> Path | None:
    configured = os.environ.get(FRONTEND_DIST_ENV)
    if configured:
        return _existing_directory(Path(configured).expanduser())

    bundled_dir = getattr(sys, "_MEIPASS", None)
    if bundled_dir:
        found = _existing_directory(Path(bundled_dir) / "frontend_dist")
        if found is not None:
            return found

    executable_dir = Path(sys.executable).resolve().parent
    found = _existing_directory(executable_dir / "frontend_dist")
    if found is not None:
        return found

    project_root = Path(__file__).resolve().parents[2]
    return _existing_directory(project_root / "frontend" / "dist")


def _existing_directory(path: Path) -> Path | None:
    return path if path.exists() and path.is_dir() else None
