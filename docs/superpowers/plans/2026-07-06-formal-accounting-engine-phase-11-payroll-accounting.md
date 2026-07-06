# 正式核算引擎十一期 薪酬社保个税正式核算 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将工资管理 MVP 升级为正式薪酬核算模块，支持工资计提、社保公积金计提、个税代扣、工资支付和正式分录生成。  
**Architecture:** 新增 `payroll_accounting` 模型和服务，工资计算结果继续由现有 `payroll_service` 生成，正式核算层负责把工资、企业社保、公积金、个税和实发工资转为应付职工薪酬、其他应付款、应交税费和银行付款分录。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录服务可幂等创建正式分录。
- 三期辅助核算支持 `employee`、`department`、`cost_center` 维度。
- 四期期末处理可运行工资计提动作。
- 现有工资管理 MVP 可计算应发、社保、公积金、个税和实发工资。
- 九期银行对账可以接收工资付款分录进行资金核对。

本期不做真实银行代发接口、不发送工资条、不做累计预扣预缴完整申报、不保存身份证号和银行卡号明文。

## 核算决策

- 工资计提以工资批次为来源，source key 为 `payroll_accrual:{account_set_id}:{period}:{payroll_batch_id}`。
- 工资费用按部门或成本中心借记 `6602 管理费用`、`6601 销售费用`、`5101 制造费用` 或配置科目。
- 员工工资贷记 `2211 应付职工薪酬-工资`。
- 企业承担社保和公积金贷记 `2211 应付职工薪酬-社保公积金`。
- 个人社保、公积金和个税在工资发放时从应付工资中扣除，贷记 `2241 其他应付款` 或 `2221 应交税费-个人所得税`。
- 实发工资付款借记 `2211 应付职工薪酬`，贷记 `1002 银行存款`。
- 已关闭期间不能新增工资计提、冲销或发放分录。

## 文件结构

- Create: `backend/app/models/payroll_accounting.py`
- Create: `backend/app/services/payroll_accounting_service.py`
- Create: `backend/app/api/payroll_accounting.py`
- Modify: `backend/app/services/payroll_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/app/api/router_registry.py`
- Create: `backend/tests/test_payroll_accounting_service.py`
- Create: `backend/tests/test_payroll_accounting_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/payrollAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/PayrollPanel.tsx`
- Create: `frontend/tests/payrollAccountingApi.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 工资批次核算模型

**Files:**
- Create: `backend/app/models/payroll_accounting.py`
- Test: `backend/tests/test_payroll_accounting_service.py`

- [ ] **Step 1: Write failing model test**

```python
from decimal import Decimal

from app.models.payroll_accounting import PayrollAccountingBatchCreate


def test_payroll_accounting_batch_keeps_amount_breakdown():
    batch = PayrollAccountingBatchCreate(
        account_set_id="default",
        period="2026-06",
        payroll_batch_id="PAY-2026-06",
        gross_salary=Decimal("100000.00"),
        employee_social_security=Decimal("10500.00"),
        employee_housing_fund=Decimal("7000.00"),
        individual_income_tax=Decimal("3000.00"),
        net_salary=Decimal("79500.00"),
        employer_social_security=Decimal("26300.00"),
        employer_housing_fund=Decimal("7000.00"),
    )

    assert batch.net_salary == Decimal("79500.00")
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py::test_payroll_accounting_batch_keeps_amount_breakdown -v
```

Expected result: fails because payroll accounting models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PayrollAccountingStatus = Literal["calculated", "accrued", "paid", "reversed"]


class PayrollAccountingBatchCreate(BaseModel):
    account_set_id: str
    period: str
    payroll_batch_id: str
    gross_salary: Decimal = Field(ge=Decimal("0"))
    employee_social_security: Decimal = Field(ge=Decimal("0"))
    employee_housing_fund: Decimal = Field(ge=Decimal("0"))
    individual_income_tax: Decimal = Field(ge=Decimal("0"))
    net_salary: Decimal = Field(ge=Decimal("0"))
    employer_social_security: Decimal = Field(ge=Decimal("0"))
    employer_housing_fund: Decimal = Field(ge=Decimal("0"))


class PayrollAccountingBatch(PayrollAccountingBatchCreate):
    status: PayrollAccountingStatus = "calculated"
    accrual_journal_entry_id: str | None = None
    payment_journal_entry_id: str | None = None
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py::test_payroll_accounting_batch_keeps_amount_breakdown -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/payroll_accounting.py backend/tests/test_payroll_accounting_service.py
git commit -m "feat: add payroll accounting batch models"
```

## Task 2: 工资和企业社保公积金计提

**Files:**
- Create: `backend/app/services/payroll_accounting_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Test: `backend/tests/test_payroll_accounting_service.py`

- [ ] **Step 1: Add failing accrual test**

```python
from app.services.payroll_accounting_service import accrue_payroll_batch


def test_accrue_payroll_batch_creates_salary_and_employer_cost_entry():
    result = accrue_payroll_batch("default", "2026-06", "PAY-2026-06", "payroll-user")

    assert result.source_id == "payroll_accrual:default:2026-06:PAY-2026-06"
    assert result.journal_entry_id.startswith("je-")
```

- [ ] **Step 2: Implement accrual lines**

```python
def build_payroll_accrual_lines(batch):
    employer_cost = batch.employer_social_security + batch.employer_housing_fund
    return [
        {"account_code": "6602", "debit": batch.gross_salary, "credit": Decimal("0.00"), "summary": "计提工资"},
        {"account_code": "6602", "debit": employer_cost, "credit": Decimal("0.00"), "summary": "计提企业社保公积金"},
        {"account_code": "2211", "debit": Decimal("0.00"), "credit": batch.gross_salary, "summary": "应付职工薪酬-工资"},
        {"account_code": "2211", "debit": Decimal("0.00"), "credit": employer_cost, "summary": "应付职工薪酬-社保公积金"},
    ]
```

- [ ] **Step 3: Implement accrual service**

```python
def accrue_payroll_batch(account_set_id: str, period: str, payroll_batch_id: str, actor_id: str):
    batch = get_payroll_accounting_batch(account_set_id, period, payroll_batch_id)
    source_id = f"payroll_accrual:{account_set_id}:{period}:{payroll_batch_id}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="payroll_accrual",
        source_id=source_id,
        lines=build_payroll_accrual_lines(batch),
        created_by=actor_id,
    )
```

- [ ] **Step 4: Run accrual tests**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py::test_accrue_payroll_batch_creates_salary_and_employer_cost_entry -v
```

Expected result: accrual creates one balanced formal entry.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/payroll_accounting_service.py backend/app/services/period_close_service.py backend/tests/test_payroll_accounting_service.py
git commit -m "feat: accrue payroll to formal ledger"
```

## Task 3: 个税、个人社保公积金和工资发放

**Files:**
- Modify: `backend/app/services/payroll_accounting_service.py`
- Test: `backend/tests/test_payroll_accounting_service.py`

- [ ] **Step 1: Add failing payment test**

```python
from app.services.payroll_accounting_service import pay_payroll_batch


def test_pay_payroll_batch_posts_deductions_and_bank_payment():
    result = pay_payroll_batch("default", "2026-06", "PAY-2026-06", "1002", "payroll-user")

    assert result.source_id == "payroll_payment:default:2026-06:PAY-2026-06"
```

- [ ] **Step 2: Implement payment lines**

```python
def build_payroll_payment_lines(batch, bank_account_code: str):
    employee_deductions = batch.employee_social_security + batch.employee_housing_fund + batch.individual_income_tax
    return [
        {"account_code": "2211", "debit": batch.gross_salary, "credit": Decimal("0.00"), "summary": "冲减应付工资"},
        {"account_code": "2241", "debit": Decimal("0.00"), "credit": batch.employee_social_security + batch.employee_housing_fund, "summary": "代扣个人社保公积金"},
        {"account_code": "2221", "debit": Decimal("0.00"), "credit": batch.individual_income_tax, "summary": "代扣个人所得税"},
        {"account_code": bank_account_code, "debit": Decimal("0.00"), "credit": batch.gross_salary - employee_deductions, "summary": "发放实发工资"},
    ]
```

- [ ] **Step 3: Run payment tests**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py -v
```

Expected result: payment entry is balanced and uses bank account credit line.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/payroll_accounting_service.py backend/tests/test_payroll_accounting_service.py
git commit -m "feat: post payroll payment entries"
```

## Task 4: 社保公积金和个税缴纳

**Files:**
- Modify: `backend/app/services/payroll_accounting_service.py`
- Test: `backend/tests/test_payroll_accounting_service.py`

- [ ] **Step 1: Add failing remittance test**

```python
from app.services.payroll_accounting_service import remit_payroll_liabilities


def test_remit_payroll_liabilities_posts_tax_and_social_security_payments():
    result = remit_payroll_liabilities("default", "2026-07", "PAY-2026-06", "1002", "payroll-user")

    assert result.source_id == "payroll_liability_payment:default:2026-07:PAY-2026-06"
```

- [ ] **Step 2: Implement liability payment lines**

```python
def build_payroll_liability_payment_lines(batch, bank_account_code: str):
    social_and_fund = batch.employee_social_security + batch.employee_housing_fund + batch.employer_social_security + batch.employer_housing_fund
    total_payment = social_and_fund + batch.individual_income_tax
    return [
        {"account_code": "2211", "debit": batch.employer_social_security + batch.employer_housing_fund, "credit": Decimal("0.00"), "summary": "缴纳企业社保公积金"},
        {"account_code": "2241", "debit": batch.employee_social_security + batch.employee_housing_fund, "credit": Decimal("0.00"), "summary": "缴纳个人社保公积金"},
        {"account_code": "2221", "debit": batch.individual_income_tax, "credit": Decimal("0.00"), "summary": "缴纳个人所得税"},
        {"account_code": bank_account_code, "debit": Decimal("0.00"), "credit": total_payment, "summary": "银行支付薪酬相关款项"},
    ]
```

- [ ] **Step 3: Run remittance tests**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py -v
```

Expected result: remittance entry is balanced.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/payroll_accounting_service.py backend/tests/test_payroll_accounting_service.py
git commit -m "feat: remit payroll liabilities"
```

## Task 5: API、权限、前端和文档

**Files:**
- Create: `backend/app/api/payroll_accounting.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_payroll_accounting_api.py`
- Create: `frontend/src/types/payrollAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/PayrollPanel.tsx`
- Create: `frontend/tests/payrollAccountingApi.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/payroll-accounting/batches`
- `POST /api/v1/payroll-accounting/accruals`
- `POST /api/v1/payroll-accounting/payments`
- `POST /api/v1/payroll-accounting/liability-payments`

Permissions:
- `payroll_accounting.read`
- `payroll_accounting.accrue`
- `payroll_accounting.pay`
- `payroll_accounting.remit`

Audit events:
- `payroll_accounting.batch.read`
- `payroll_accounting.accrual.post`
- `payroll_accounting.payment.post`
- `payroll_accounting.liability_payment.post`

- [ ] **Step 2: Update PayrollPanel**

Panel must show:
- 工资批次状态。
- 计提分录号。
- 发放分录号。
- 个税和社保公积金缴纳状态。
- 期间关闭提示。

- [ ] **Step 3: Run regression**

```powershell
python -m pytest backend/tests/test_payroll_accounting_service.py backend/tests/test_payroll_accounting_api.py backend/tests/test_payroll_service.py backend/tests/test_period_close_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/payroll_accounting.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_payroll_accounting_api.py frontend/src/types/payrollAccounting.ts frontend/src/services/dashboardApi.ts frontend/src/components/PayrollPanel.tsx frontend/tests/payrollAccountingApi.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: expose payroll accounting workflow"
```

## 验收标准

- 工资批次可生成工资计提正式分录。
- 实发工资可生成银行付款正式分录。
- 个税、个人社保公积金和企业社保公积金可生成缴纳分录。
- 工资批次状态能区分已计算、已计提、已发放和已冲销。
- 已关闭期间拒绝新增计提、发放和缴纳分录。
- API、权限、审计和前端状态展示完整。

## 风险控制

- 不保存身份证号、银行卡号和手机号明文。
- 工资批次 source key 必须包含账套、期间和批次号。
- 每个批次每类分录只能幂等生成一次。
- 工资支付前必须存在计提分录。
- 金额统一使用 `Decimal`。
