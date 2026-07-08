import hashlib
import json
import os
import re
import urllib.request
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from app.models.policy import PolicyDocument
from app.models.update_center import (
    ApplicationUpdateCheckResult,
    ApplicationUpdateManifest,
    PolicyPackageManifest,
    UpdateCenterConfig,
    UpdateCenterEvent,
    UpdateCenterStatus,
    UpdateCheckResult,
)
from app.runtime_paths import get_user_data_dir


UPDATE_MANIFEST_ENV = "FINANCE_AI_UPDATE_MANIFEST_URL"
APP_UPDATE_MANIFEST_ENV = "FINANCE_AI_APP_UPDATE_MANIFEST_URL"
UPDATE_CHANNEL_ENV = "FINANCE_AI_UPDATE_CHANNEL"
UPDATE_AUTO_ENV = "FINANCE_AI_AUTO_UPDATE"
UPDATE_PROXY_ENV = "FINANCE_AI_UPDATE_PROXY"
UPDATE_STATE_FILENAME = "update-center.json"
POLICY_PACKAGE_DIRNAME = "policy-packages"
APP_UPDATE_DIRNAME = "app-updates"
CURRENT_APP_VERSION = "0.1.0"


def get_update_status(now: datetime | None = None) -> UpdateCenterStatus:
    status = _load_status()
    status.config = _config_from_environment(status.config)
    status.next_scheduled_check = _next_scheduled_check(now or datetime.now(), status.config.schedule_day)
    return status


def should_run_monthly_update(status: UpdateCenterStatus, now: datetime) -> bool:
    if not status.config.auto_update_enabled:
        return False
    if now.day != status.config.schedule_day:
        return False
    return status.last_scheduled_check_month != _month_key(now)


def record_scheduled_update_attempt(now: datetime | None = None) -> UpdateCenterStatus:
    checked_at = now or datetime.now()
    status = get_update_status(now=checked_at)
    status.last_scheduled_check_at = checked_at
    status.last_scheduled_check_month = _month_key(checked_at)
    _append_event(status, "monthly_schedule", "scheduled", "已记录本月自动更新检查窗口", checked_at)
    _save_status(status)
    return status


def run_scheduled_update(
    fetch_bytes: Callable[[str], bytes] | None = None,
    now: datetime | None = None,
) -> UpdateCheckResult | None:
    checked_at = now or datetime.now()
    status = get_update_status(now=checked_at)
    if not should_run_monthly_update(status, checked_at):
        return None
    record_scheduled_update_attempt(checked_at)
    result = check_for_updates(fetch_bytes=fetch_bytes, now=checked_at)
    check_for_application_update(fetch_bytes=fetch_bytes, now=checked_at)
    return result


def check_for_updates(
    fetch_bytes: Callable[[str], bytes] | None = None,
    now: datetime | None = None,
) -> UpdateCheckResult:
    checked_at = now or datetime.now()
    status = get_update_status(now=checked_at)
    status.last_checked_at = checked_at

    if not status.config.manifest_url:
        result = _result("not_configured", "未配置联网更新清单地址", status, checked_at)
        status.online_status = "not_configured"
        _append_event(status, "manual_check", result.status, result.message, checked_at)
        _save_status(status)
        return result

    if not _is_https_url(status.config.manifest_url):
        return _fail(status, checked_at, "更新清单地址必须使用 HTTPS")

    fetcher = fetch_bytes or _fetch_url_bytes
    try:
        manifest_payload = fetcher(status.config.manifest_url)
        manifest = PolicyPackageManifest.model_validate_json(manifest_payload)
        package_url = str(manifest.package_url)
        if not _is_https_url(package_url):
            return _fail(status, checked_at, "政策包地址必须使用 HTTPS")

        if manifest.version == status.current_policy_version:
            result = _result("up_to_date", f"当前已是最新政策包 {manifest.version}", status, checked_at, manifest.version)
            status.online_status = "online"
            status.last_error = None
            _append_event(status, "manual_check", result.status, result.message, checked_at)
            _save_status(status)
            return result

        package_payload = fetcher(package_url)
        digest = hashlib.sha256(package_payload).hexdigest()
        if digest.lower() != manifest.sha256.lower():
            return _fail(status, checked_at, f"政策包 SHA256 校验失败：期望 {manifest.sha256}，实际 {digest}", manifest.version)

        package_path = _write_policy_package(manifest.version, package_payload)
        status.current_policy_version = manifest.version
        status.current_policy_package_path = str(package_path)
        status.online_status = "online"
        status.last_successful_update_at = checked_at
        status.last_error = None
        result = _result("updated", f"已更新到政策包 {manifest.version}", status, checked_at, manifest.version)
        _append_event(status, "manual_check", result.status, result.message, checked_at)
        _save_status(status)
        return result
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        return _fail(status, checked_at, f"联网更新失败：{exc}")


def check_for_application_update(
    fetch_bytes: Callable[[str], bytes] | None = None,
    now: datetime | None = None,
) -> ApplicationUpdateCheckResult:
    checked_at = now or datetime.now()
    status = get_update_status(now=checked_at)
    status.current_app_version = CURRENT_APP_VERSION
    status.last_checked_at = checked_at

    if not status.config.app_manifest_url:
        result = _app_result("not_configured", "未配置软件本体更新清单地址", status, checked_at)
        status.online_status = "not_configured"
        _append_event(status, "application_check", result.status, result.message, checked_at)
        _save_status(status)
        return result

    if not _is_https_url(status.config.app_manifest_url):
        return _app_fail(status, checked_at, "软件本体更新清单地址必须使用 HTTPS")

    fetcher = fetch_bytes or _fetch_url_bytes
    try:
        manifest_payload = fetcher(status.config.app_manifest_url)
        manifest = ApplicationUpdateManifest.model_validate_json(manifest_payload)
        package_url = str(manifest.package_url)
        if not _is_https_url(package_url):
            return _app_fail(status, checked_at, "软件本体更新包地址必须使用 HTTPS")

        if _compare_versions(manifest.version, CURRENT_APP_VERSION) <= 0:
            status.available_app_version = manifest.version
            status.app_update_required = False
            status.online_status = "online"
            status.last_error = None
            result = _app_result(
                "up_to_date",
                f"当前软件已是最新版本 {CURRENT_APP_VERSION}",
                status,
                checked_at,
                manifest.version,
                None,
                manifest.mandatory,
            )
            _append_event(status, "application_check", result.status, result.message, checked_at)
            _save_status(status)
            return result

        package_payload = fetcher(package_url)
        digest = hashlib.sha256(package_payload).hexdigest()
        if digest.lower() != manifest.sha256.lower():
            return _app_fail(
                status,
                checked_at,
                f"软件本体更新包 SHA256 校验失败：期望 {manifest.sha256}，实际 {digest}",
            )

        package_path = _write_app_update_package(manifest.version, package_payload)
        status.available_app_version = manifest.version
        status.app_update_package_path = str(package_path)
        status.app_update_required = manifest.mandatory
        status.online_status = "online"
        status.last_error = None
        result = _app_result(
            "updated",
            f"已下载软件本体更新包 {manifest.version}",
            status,
            checked_at,
            manifest.version,
            str(package_path),
            manifest.mandatory,
        )
        _append_event(status, "application_check", result.status, result.message, checked_at)
        _save_status(status)
        return result
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        return _app_fail(status, checked_at, f"软件本体联网更新失败：{exc}")


def load_installed_policy_documents() -> tuple[PolicyDocument, ...]:
    status = get_update_status()
    if not status.current_policy_package_path:
        return ()
    package_path = Path(status.current_policy_package_path)
    if not package_path.exists():
        return ()
    try:
        payload = json.loads(package_path.read_text(encoding="utf-8"))
        return tuple(PolicyDocument.model_validate(item) for item in payload.get("documents", []))
    except (OSError, ValueError, ValidationError, TypeError):
        return ()


def _load_status() -> UpdateCenterStatus:
    path = _state_path()
    if not path.exists():
        return UpdateCenterStatus()
    try:
        return UpdateCenterStatus.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError):
        return UpdateCenterStatus()


def _save_status(status: UpdateCenterStatus) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _state_path() -> Path:
    return get_user_data_dir() / UPDATE_STATE_FILENAME


def _package_dir() -> Path:
    return get_user_data_dir() / POLICY_PACKAGE_DIRNAME


def _app_update_dir() -> Path:
    return get_user_data_dir() / APP_UPDATE_DIRNAME


def _write_policy_package(version: str, payload: bytes) -> Path:
    package_dir = _package_dir()
    package_dir.mkdir(parents=True, exist_ok=True)
    safe_version = re.sub(r"[^0-9A-Za-z_.-]+", "-", version).strip("-") or "latest"
    package_path = package_dir / f"policy-{safe_version}.json"
    package_path.write_bytes(payload)
    return package_path


def _write_app_update_package(version: str, payload: bytes) -> Path:
    package_dir = _app_update_dir()
    package_dir.mkdir(parents=True, exist_ok=True)
    safe_version = re.sub(r"[^0-9A-Za-z_.-]+", "-", version).strip("-") or "latest"
    package_path = package_dir / f"app-{safe_version}.zip"
    package_path.write_bytes(payload)
    return package_path


def _fetch_url_bytes(url: str) -> bytes:
    status = get_update_status()
    proxy_url = status.config.proxy_url
    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy_url}))
        if proxy_url
        else urllib.request.build_opener()
    )
    request = urllib.request.Request(url, headers={"User-Agent": "ChinaFinanceAIAssistant/0.1"})
    with opener.open(request, timeout=20) as response:
        return response.read()


def _config_from_environment(saved: UpdateCenterConfig) -> UpdateCenterConfig:
    auto_update_enabled = saved.auto_update_enabled
    auto_value = os.environ.get(UPDATE_AUTO_ENV)
    if auto_value is not None:
        auto_update_enabled = auto_value.strip().lower() not in {"0", "false", "no", "off"}

    return saved.model_copy(
        update={
            "provider": saved.provider or "codex",
            "auto_update_enabled": auto_update_enabled,
            "schedule_day": saved.schedule_day or 1,
            "update_channel": os.environ.get(UPDATE_CHANNEL_ENV, saved.update_channel),
            "manifest_url": os.environ.get(UPDATE_MANIFEST_ENV, saved.manifest_url),
            "app_manifest_url": os.environ.get(APP_UPDATE_MANIFEST_ENV, saved.app_manifest_url),
            "proxy_url": os.environ.get(UPDATE_PROXY_ENV, saved.proxy_url),
        }
    )


def _next_scheduled_check(now: datetime, schedule_day: int) -> datetime:
    if now.day <= schedule_day:
        return now.replace(day=schedule_day, hour=9, minute=0, second=0, microsecond=0)
    year = now.year + 1 if now.month == 12 else now.year
    month = 1 if now.month == 12 else now.month + 1
    return now.replace(year=year, month=month, day=schedule_day, hour=9, minute=0, second=0, microsecond=0)


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _append_event(
    status: UpdateCenterStatus,
    event: str,
    result_status: str,
    message: str,
    created_at: datetime,
) -> None:
    status.events.insert(
        0,
        UpdateCenterEvent(event=event, status=result_status, message=message, created_at=created_at),
    )
    status.events = status.events[:20]


def _result(
    result_status: str,
    message: str,
    status: UpdateCenterStatus,
    checked_at: datetime,
    manifest_version: str | None = None,
) -> UpdateCheckResult:
    return UpdateCheckResult(
        status=result_status,
        message=message,
        current_policy_version=status.current_policy_version,
        checked_at=checked_at,
        manifest_version=manifest_version,
    )


def _fail(
    status: UpdateCenterStatus,
    checked_at: datetime,
    message: str,
    manifest_version: str | None = None,
) -> UpdateCheckResult:
    status.online_status = "failed"
    status.last_error = message
    result = _result("failed", message, status, checked_at, manifest_version)
    _append_event(status, "manual_check", result.status, result.message, checked_at)
    _save_status(status)
    return result


def _is_https_url(url: str) -> bool:
    return urlparse(url).scheme.lower() == "https"


def _app_result(
    result_status: str,
    message: str,
    status: UpdateCenterStatus,
    checked_at: datetime,
    available_app_version: str | None = None,
    update_package_path: str | None = None,
    mandatory: bool = False,
) -> ApplicationUpdateCheckResult:
    return ApplicationUpdateCheckResult(
        status=result_status,
        message=message,
        current_app_version=CURRENT_APP_VERSION,
        checked_at=checked_at,
        available_app_version=available_app_version,
        update_package_path=update_package_path,
        mandatory=mandatory,
    )


def _app_fail(
    status: UpdateCenterStatus,
    checked_at: datetime,
    message: str,
) -> ApplicationUpdateCheckResult:
    status.online_status = "failed"
    status.last_error = message
    result = _app_result("failed", message, status, checked_at)
    _append_event(status, "application_check", result.status, result.message, checked_at)
    _save_status(status)
    return result


def _compare_versions(left: str, right: str) -> int:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    max_length = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (max_length - len(left_parts)))
    right_parts.extend([0] * (max_length - len(right_parts)))
    if left_parts == right_parts:
        return 0
    return 1 if left_parts > right_parts else -1


def _version_parts(value: str) -> list[int]:
    return [int(part) for part in re.findall(r"\d+", value)]
