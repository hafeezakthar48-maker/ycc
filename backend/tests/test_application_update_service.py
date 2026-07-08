import hashlib
import json
from datetime import datetime

from app.services.update_center_service import check_for_application_update, get_update_status


def test_check_for_application_update_downloads_newer_https_package(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_APP_UPDATE_MANIFEST_URL", "https://updates.example.test/app/manifest.json")
    package = b"fake application update zip"
    manifest = {
        "version": "0.2.0",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/app/ChinaFinanceAIAssistant-0.2.0.zip",
        "sha256": hashlib.sha256(package).hexdigest(),
        "summary": "软件本体 0.2.0 更新包",
        "mandatory": False,
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return package

    result = check_for_application_update(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))
    status = get_update_status()

    assert result.status == "updated"
    assert result.available_app_version == "0.2.0"
    assert result.update_package_path is not None
    assert status.available_app_version == "0.2.0"
    assert status.app_update_package_path is not None
    assert status.app_update_package_path.endswith("app-0.2.0.zip")


def test_check_for_application_update_reports_up_to_date_for_current_version(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_APP_UPDATE_MANIFEST_URL", "https://updates.example.test/app/manifest.json")
    manifest = {
        "version": "0.1.0",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/app/ChinaFinanceAIAssistant-0.1.0.zip",
        "sha256": "a" * 64,
        "summary": "当前版本",
        "mandatory": False,
    }

    result = check_for_application_update(
        fetch_bytes=lambda _url: json.dumps(manifest).encode("utf-8"),
        now=datetime(2026, 8, 1, 9, 0, 0),
    )

    assert result.status == "up_to_date"
    assert result.current_app_version == "0.1.0"
    assert result.available_app_version == "0.1.0"


def test_check_for_application_update_rejects_http_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_APP_UPDATE_MANIFEST_URL", "http://updates.example.test/app/manifest.json")

    result = check_for_application_update(now=datetime(2026, 8, 1, 9, 0, 0))

    assert result.status == "failed"
    assert "HTTPS" in result.message


def test_check_for_application_update_rejects_sha256_mismatch(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_APP_UPDATE_MANIFEST_URL", "https://updates.example.test/app/manifest.json")
    manifest = {
        "version": "0.2.0",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/app/ChinaFinanceAIAssistant-0.2.0.zip",
        "sha256": "0" * 64,
        "summary": "软件本体 0.2.0 更新包",
        "mandatory": False,
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return b"bad package"

    result = check_for_application_update(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))

    assert result.status == "failed"
    assert result.available_app_version is None
    assert "SHA256" in result.message
