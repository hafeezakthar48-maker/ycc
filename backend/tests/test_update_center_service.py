import hashlib
import json
from datetime import datetime

from app.models.policy import PolicySearchRequest
from app.services.policy_library_service import search_policy_documents
from app.services.update_center_service import (
    check_for_updates,
    get_update_status,
    record_scheduled_update_attempt,
    should_run_monthly_update,
)


def test_monthly_auto_update_runs_on_first_day_when_not_checked(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    status = get_update_status(now=datetime(2026, 8, 1, 9, 0, 0))

    assert status.config.provider == "codex"
    assert status.config.auto_update_enabled is True
    assert status.config.schedule_day == 1
    assert should_run_monthly_update(status, datetime(2026, 8, 1, 9, 0, 0)) is True


def test_monthly_auto_update_does_not_repeat_after_attempt_in_same_month(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))

    record_scheduled_update_attempt(datetime(2026, 8, 1, 9, 0, 0))
    status = get_update_status(now=datetime(2026, 8, 1, 10, 0, 0))

    assert should_run_monthly_update(status, datetime(2026, 8, 1, 10, 0, 0)) is False


def test_check_for_updates_accepts_https_manifest_and_records_version(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_UPDATE_MANIFEST_URL", "https://updates.example.test/manifest.json")
    package = b'{"documents":[]}'
    manifest = {
        "version": "2026.08",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/policy-2026-08.json",
        "sha256": hashlib.sha256(package).hexdigest(),
        "summary": "2026年8月法规政策包",
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return package

    result = check_for_updates(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))

    assert result.status == "updated"
    assert result.current_policy_version == "2026.08"
    assert result.message == "已更新到政策包 2026.08"
    assert get_update_status().current_policy_version == "2026.08"


def test_check_for_updates_rejects_sha256_mismatch_without_replacing_version(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_UPDATE_MANIFEST_URL", "https://updates.example.test/manifest.json")
    manifest = {
        "version": "2026.08",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/policy-2026-08.json",
        "sha256": "0" * 64,
        "summary": "2026年8月法规政策包",
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return b'{"documents":[]}'

    result = check_for_updates(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))

    assert result.status == "failed"
    assert result.current_policy_version == "local-bundled"
    assert "SHA256" in result.message


def test_installed_policy_package_participates_in_policy_search(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FINANCE_AI_UPDATE_MANIFEST_URL", "https://updates.example.test/manifest.json")
    package = {
        "documents": [
            {
                "id": "monthly-policy-2026-08",
                "title": "2026年8月月度联网政策测试卡片",
                "authority": "Codex更新中心",
                "document_number": "AUTO-2026-08",
                "category": "税收法规",
                "published_date": "2026-08-01",
                "effective_date": "2026-08-01",
                "status": "需复核",
                "source_url": "https://updates.example.test/policy-2026-08.html",
                "updated_at": "2026-08-01",
                "keywords": ["月度联网更新", "自动政策包"],
                "summary": "用于验证联网政策包安装后可参与本地法规检索。",
                "content": "企业正式使用前仍需由财务或税务负责人复核政策来源与适用口径。",
            }
        ]
    }
    package_bytes = json.dumps(package, ensure_ascii=False).encode("utf-8")
    manifest = {
        "version": "2026.08",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/policy-2026-08.json",
        "sha256": hashlib.sha256(package_bytes).hexdigest(),
        "summary": "2026年8月法规政策包",
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return package_bytes

    check_for_updates(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))
    response = search_policy_documents(PolicySearchRequest(query="月度联网更新", limit=3))

    assert response.results[0].document.id == "monthly-policy-2026-08"
