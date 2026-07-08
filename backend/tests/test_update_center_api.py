from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_update_center_status_endpoint_returns_monthly_codex_config(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("FINANCE_AI_UPDATE_MANIFEST_URL", raising=False)

    response = client.get("/api/v1/update-center/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["config"]["provider"] == "codex"
    assert payload["config"]["auto_update_enabled"] is True
    assert payload["config"]["schedule_day"] == 1
    assert payload["current_policy_version"] == "local-bundled"
    assert payload["next_scheduled_check"] is not None


def test_update_center_manual_check_is_safe_when_manifest_is_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("FINANCE_AI_UPDATE_MANIFEST_URL", raising=False)

    response = client.post("/api/v1/update-center/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_configured"
    assert payload["current_policy_version"] == "local-bundled"
    assert "未配置" in payload["message"]


def test_update_center_application_check_is_safe_when_manifest_is_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("FINANCE_AI_APP_UPDATE_MANIFEST_URL", raising=False)

    response = client.post("/api/v1/update-center/application/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_configured"
    assert payload["current_app_version"] == "0.1.0"
    assert "未配置" in payload["message"]
