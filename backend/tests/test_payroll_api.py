from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def _payload(account_set_id: str = "default"):
    return {
        "account_set_id": account_set_id,
        "period": "2026-06",
        "operator": "财务主管",
        "employees": [
            {
                "employee_id": "E001",
                "employee_name": "张会计",
                "department": "财务部",
                "base_salary": "20000.00",
                "bonus": "0.00",
                "allowance": "0.00",
                "social_security_base": "20000.00",
                "housing_fund_base": "20000.00",
                "special_additional_deduction": "1000.00",
            }
        ],
    }


def test_payroll_api_calculates_salary_and_records_success_audit():
    reset_system_admin_store()

    response = client.post(
        "/api/v1/payroll/calculate",
        headers={"X-Actor-Id": "u-finance-manager"},
        json=_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_set_id"] == "default"
    assert payload["summary"]["employee_count"] == 1
    assert Decimal(str(payload["summary"]["net_pay_total"])) == Decimal("15660.00")
    assert payload["employees"][0]["employee_name"] == "张会计"
    assert Decimal(str(payload["employees"][0]["individual_income_tax"])) == Decimal("840.00")

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "payroll.calculate"
    assert log["actor_id"] == "u-finance-manager"
    assert log["result"] == "success"
    assert log["metadata"]["account_set_id"] == "default"
    assert log["metadata"]["period"] == "2026-06"
    assert log["metadata"]["employee_count"] == 1


def test_payroll_api_rejects_unauthorized_actor_and_records_denied_audit():
    reset_system_admin_store()

    response = client.post(
        "/api/v1/payroll/calculate",
        headers={"X-Actor-Id": "u-api-integrator"},
        json=_payload(),
    )

    assert response.status_code == 403
    assert "权限不足" in response.json()["detail"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "payroll.calculate"
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "payroll.calculate"


def test_finance_center_registry_declares_payroll_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/payroll" in module["api_prefixes"]
    assert "payroll.calculate" in module["audit_events"]
