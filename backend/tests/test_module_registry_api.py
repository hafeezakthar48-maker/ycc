from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


EXPECTED_MODULE_IDS = [
    "ai-home",
    "finance-center",
    "tax-center",
    "analysis-center",
    "bi-center",
    "ecommerce-center",
    "ocr-center",
    "knowledge-base",
    "ai-assistant",
    "risk-center",
    "system-admin",
    "open-platform",
]


def test_module_registry_lists_frd_modules_in_order():
    response = client.get("/api/v1/modules")

    assert response.status_code == 200
    modules = response.json()["modules"]

    assert [module["id"] for module in modules] == EXPECTED_MODULE_IDS
    assert all(module["requires_permission"] is True for module in modules)
    for module in modules:
        assert module["label"]
        assert module["status"] in {"mvp", "planned"}
        assert module["api_prefixes"]
        assert len(module["capabilities"]) >= 3
        assert module["audit_events"]
        assert module["rate_limit_policy"]


def test_open_platform_registry_declares_api_governance_capabilities():
    response = client.get("/api/v1/modules/open-platform")

    assert response.status_code == 200
    module = response.json()

    assert module["id"] == "open-platform"
    assert module["api_prefixes"] == ["/api/v1/platform"]
    assert {
        "REST API",
        "Webhook",
        "OAuth2",
        "OpenAPI",
        "SDK",
        "权限控制",
        "审计日志",
        "限流",
        "版本管理",
    }.issubset(set(module["capabilities"]))


def test_finance_center_registry_declares_ledger_read_model_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/ledger" in module["api_prefixes"]
    assert "ledger.general.read" in module["audit_events"]
    assert "/api/v1/accounting-archive" in module["api_prefixes"]
    assert {
        "archive.document.list",
        "archive.document.get",
        "archive.document.create",
        "archive.case.create",
        "archive.package.download",
        "archive.verification.update",
    }.issubset(set(module["audit_events"]))
    assert "/api/v1/period-close" in module["api_prefixes"]
    assert {
        "period_close.run_started",
        "period_close.runs_viewed",
        "period_close.checks_completed",
        "period_close.actions_previewed",
        "period_close.actions_generated",
        "period_close.period_closed",
        "period_close.period_reopened",
    }.issubset(set(module["audit_events"]))


def test_unknown_module_returns_404():
    response = client.get("/api/v1/modules/not-exists")

    assert response.status_code == 404
    assert "模块不存在" in response.json()["detail"]


def test_existing_business_routes_still_registered():
    assert client.get("/api/v1/home/dashboard?period=2026-06").status_code == 200
    assert client.get("/api/v1/vouchers/center").status_code == 200
    assert client.get("/api/v1/ledger/general?period=2026-06").status_code == 200
