from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_app_settings_default_state_uses_user_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))

    response = client.get("/api/v1/app-settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_name"] == "示例制造企业"
    assert payload["default_account_set_id"] == "default"
    assert payload["current_period"] == "2026-06"
    assert payload["onboarding_completed"] is False
    assert payload["policy_manifest_url"] is None
    assert payload["app_manifest_url"] is None
    assert (tmp_path / "app-settings.json").exists()


def test_app_settings_update_persists_company_period_and_update_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path))
    payload = {
        "company_name": "杭州样例科技有限公司",
        "default_account_set_id": "hz-main",
        "current_period": "2026-07",
        "onboarding_completed": True,
        "policy_manifest_url": "https://updates.example.com/policies.json",
        "app_manifest_url": "https://updates.example.com/app.json",
    }

    response = client.put("/api/v1/app-settings", json=payload)
    second = client.get("/api/v1/app-settings")

    assert response.status_code == 200
    assert second.status_code == 200
    assert second.json()["company_name"] == "杭州样例科技有限公司"
    assert second.json()["current_period"] == "2026-07"
    assert second.json()["onboarding_completed"] is True
    assert second.json()["policy_manifest_url"] == "https://updates.example.com/policies.json"
    assert second.json()["app_manifest_url"] == "https://updates.example.com/app.json"
