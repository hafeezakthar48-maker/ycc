# 正式核算引擎十三期 税务核算与申报底稿 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立增值税、附加税、企业所得税和纳税支付的正式核算与申报底稿能力。
**Architecture:** 新增 `tax_accounting` 模型和服务，从正式分录、发票结构化结果和税务调整事项生成税务台账。申报底稿只作为计算和复核依据，正式纳税义务和缴款通过正式分录记录，不自动提交税务申报。
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录服务稳定可用。
- 二期多币种折算可提供本位币税基。
- 三期辅助核算支持客户、供应商、项目和税种维度。
- 四期期末处理可运行税费计提动作。
- 七期电子凭证归档可关联发票和凭证附件。
- 现有 OCR 发票识别可提供发票号码、金额、税额和价税合计。

本期不做税局直连申报，不自动抵扣认证，不做真实发票验真，不处理复杂税收优惠备案，不替代税务师判断。

## 核算决策

- 增值税进项税额默认读取 `2221 应交税费-应交增值税（进项税额）` 借方发生额。
- 增值税销项税额默认读取 `2221 应交税费-应交增值税（销项税额）` 贷方发生额。
- 进项税额转出借记成本费用或资产科目，贷记进项税额转出明细。
- 月末转出未交增值税：销项大于进项时借记转出未交增值税，贷记未交增值税。
- 附加税以实际应交增值税为基础计算，借记 `6403 税金及附加`，贷记 `2221 应交税费-城建税/教育费附加/地方教育附加`。
- 企业所得税按利润总额加减纳税调整后的应纳税所得额计算，借记 `6801 所得税费用`，贷记 `2221 应交税费-企业所得税`。
- 纳税支付借记应交税费明细，贷记 `1002 银行存款`。
- 已关闭期间不能新增税费计提、转出和纳税支付分录。

## 文件结构

- Create: `backend/app/models/tax_accounting.py`
- Create: `backend/app/services/tax_accounting_service.py`
- Create: `backend/app/api/tax_accounting.py`
- Modify: `backend/app/services/invoice_ocr_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/app/api/router_registry.py`
- Create: `backend/tests/test_tax_accounting_service.py`
- Create: `backend/tests/test_tax_accounting_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/taxAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/TaxAccountingPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/taxAccountingApi.test.mjs`
- Create: `frontend/tests/taxAccountingPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 税务台账模型

**Files:**
- Create: `backend/app/models/tax_accounting.py`
- Test: `backend/tests/test_tax_accounting_service.py`

- [ ] **Step 1: Write failing model test**

```python
from decimal import Decimal

from app.models.tax_accounting import VatLedgerLine


def test_vat_ledger_line_keeps_tax_base_and_tax_amount():
    line = VatLedgerLine(
        account_set_id="default",
        period="2026-06",
        tax_direction="output",
        invoice_no="INV-001",
        tax_base=Decimal("1000.00"),
        tax_amount=Decimal("130.00"),
        counterparty_id="CUST-001",
        source_journal_entry_id="je-001",
    )

    assert line.tax_amount == Decimal("130.00")
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py::test_vat_ledger_line_keeps_tax_base_and_tax_amount -v
```

Expected result: fails because tax accounting models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


VatDirection = Literal["input", "output", "input_transfer_out"]


class VatLedgerLine(BaseModel):
    account_set_id: str
    period: str
    tax_direction: VatDirection
    invoice_no: str
    tax_base: Decimal = Field(ge=Decimal("0"))
    tax_amount: Decimal = Field(ge=Decimal("0"))
    counterparty_id: str | None = None
    source_journal_entry_id: str


class TaxFilingWorksheet(BaseModel):
    account_set_id: str
    period: str
    output_vat: Decimal
    input_vat: Decimal
    input_transfer_out: Decimal
    vat_payable: Decimal
    surtax_payable: Decimal
    income_tax_payable: Decimal
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py::test_vat_ledger_line_keeps_tax_base_and_tax_amount -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/tax_accounting.py backend/tests/test_tax_accounting_service.py
git commit -m "feat: add tax accounting models"
```

## Task 2: 增值税台账与未交增值税结转

**Files:**
- Create: `backend/app/services/tax_accounting_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Test: `backend/tests/test_tax_accounting_service.py`

- [ ] **Step 1: Add failing VAT worksheet test**

```python
from decimal import Decimal

from app.services.tax_accounting_service import calculate_vat_payable


def test_calculate_vat_payable_offsets_input_against_output():
    result = calculate_vat_payable(
        output_vat=Decimal("1300.00"),
        input_vat=Decimal("800.00"),
        input_transfer_out=Decimal("100.00"),
    )

    assert result == Decimal("600.00")
```

- [ ] **Step 2: Implement VAT calculation**

```python
from decimal import Decimal


def calculate_vat_payable(output_vat: Decimal, input_vat: Decimal, input_transfer_out: Decimal) -> Decimal:
    payable = output_vat - input_vat + input_transfer_out
    return max(payable, Decimal("0.00")).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Implement unpaid VAT transfer entry**

```python
def post_unpaid_vat_transfer(account_set_id: str, period: str, amount: Decimal, actor_id: str):
    source_id = f"tax_unpaid_vat_transfer:{account_set_id}:{period}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="tax_unpaid_vat_transfer",
        source_id=source_id,
        lines=[
            {"account_code": "2221", "account_name": "应交税费-应交增值税（转出未交增值税）", "debit": amount, "credit": Decimal("0.00")},
            {"account_code": "2221", "account_name": "应交税费-未交增值税", "debit": Decimal("0.00"), "credit": amount},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 4: Run VAT tests**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py::test_calculate_vat_payable_offsets_input_against_output -v
```

Expected result: VAT payable calculation passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/tax_accounting_service.py backend/app/services/accounting_service.py backend/tests/test_tax_accounting_service.py
git commit -m "feat: calculate vat payable"
```

## Task 3: 附加税计提

**Files:**
- Modify: `backend/app/services/tax_accounting_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Test: `backend/tests/test_tax_accounting_service.py`

- [ ] **Step 1: Add failing surtax test**

```python
from decimal import Decimal

from app.services.tax_accounting_service import calculate_surtax


def test_calculate_surtax_uses_configured_rates():
    result = calculate_surtax(
        vat_payable=Decimal("1000.00"),
        urban_maintenance_rate=Decimal("0.07"),
        education_rate=Decimal("0.03"),
        local_education_rate=Decimal("0.02"),
    )

    assert result.total == Decimal("120.00")
```

- [ ] **Step 2: Implement surtax calculation**

```python
def calculate_surtax(vat_payable: Decimal, urban_maintenance_rate: Decimal, education_rate: Decimal, local_education_rate: Decimal):
    urban = (vat_payable * urban_maintenance_rate).quantize(Decimal("0.01"))
    education = (vat_payable * education_rate).quantize(Decimal("0.01"))
    local = (vat_payable * local_education_rate).quantize(Decimal("0.01"))
    return type("SurtaxResult", (), {"urban": urban, "education": education, "local": local, "total": urban + education + local})()
```

- [ ] **Step 3: Implement surtax accrual entry**

```python
def post_surtax_accrual(account_set_id: str, period: str, surtax_result, actor_id: str):
    source_id = f"tax_surtax_accrual:{account_set_id}:{period}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="tax_surtax_accrual",
        source_id=source_id,
        lines=[
            {"account_code": "6403", "debit": surtax_result.total, "credit": Decimal("0.00")},
            {"account_code": "2221", "debit": Decimal("0.00"), "credit": surtax_result.total},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 4: Run surtax tests**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py -v
```

Expected result: surtax tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/tax_accounting_service.py backend/app/services/period_close_service.py backend/tests/test_tax_accounting_service.py
git commit -m "feat: accrue vat surtaxes"
```

## Task 4: 企业所得税测算与计提

**Files:**
- Modify: `backend/app/models/tax_accounting.py`
- Modify: `backend/app/services/tax_accounting_service.py`
- Test: `backend/tests/test_tax_accounting_service.py`

- [ ] **Step 1: Add failing CIT test**

```python
from decimal import Decimal

from app.services.tax_accounting_service import calculate_income_tax_payable


def test_calculate_income_tax_payable_uses_tax_adjustments():
    result = calculate_income_tax_payable(
        accounting_profit=Decimal("100000.00"),
        taxable_increase=Decimal("5000.00"),
        taxable_decrease=Decimal("10000.00"),
        tax_rate=Decimal("0.25"),
    )

    assert result.taxable_income == Decimal("95000.00")
    assert result.income_tax_payable == Decimal("23750.00")
```

- [ ] **Step 2: Implement CIT calculation**

```python
def calculate_income_tax_payable(accounting_profit: Decimal, taxable_increase: Decimal, taxable_decrease: Decimal, tax_rate: Decimal):
    taxable_income = max(accounting_profit + taxable_increase - taxable_decrease, Decimal("0.00")).quantize(Decimal("0.01"))
    income_tax_payable = (taxable_income * tax_rate).quantize(Decimal("0.01"))
    return type("IncomeTaxResult", (), {"taxable_income": taxable_income, "income_tax_payable": income_tax_payable})()
```

- [ ] **Step 3: Implement income tax accrual entry**

```python
def post_income_tax_accrual(account_set_id: str, period: str, amount: Decimal, actor_id: str):
    source_id = f"tax_income_tax_accrual:{account_set_id}:{period}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="tax_income_tax_accrual",
        source_id=source_id,
        lines=[
            {"account_code": "6801", "debit": amount, "credit": Decimal("0.00")},
            {"account_code": "2221", "debit": Decimal("0.00"), "credit": amount},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 4: Run CIT tests**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py -v
```

Expected result: CIT tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/tax_accounting.py backend/app/services/tax_accounting_service.py backend/tests/test_tax_accounting_service.py
git commit -m "feat: calculate corporate income tax"
```

## Task 5: 纳税支付和申报底稿 API

**Files:**
- Create: `backend/app/api/tax_accounting.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_tax_accounting_api.py`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/tax-accounting/vat-ledger`
- `GET /api/v1/tax-accounting/filing-worksheet`
- `POST /api/v1/tax-accounting/unpaid-vat-transfer`
- `POST /api/v1/tax-accounting/surtax-accrual`
- `POST /api/v1/tax-accounting/income-tax-accrual`
- `POST /api/v1/tax-accounting/tax-payments`

Permissions:
- `tax_accounting.read`
- `tax_accounting.accrue`
- `tax_accounting.pay`

Audit events:
- `tax_accounting.vat_ledger.read`
- `tax_accounting.worksheet.read`
- `tax_accounting.vat.transfer`
- `tax_accounting.surtax.accrue`
- `tax_accounting.income_tax.accrue`
- `tax_accounting.payment.post`

- [ ] **Step 2: Implement tax payment entry**

```python
def post_tax_payment(account_set_id: str, period: str, tax_account_name: str, amount: Decimal, bank_account_code: str, actor_id: str):
    source_id = f"tax_payment:{account_set_id}:{period}:{tax_account_name}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-15",
        source_type="tax_payment",
        source_id=source_id,
        lines=[
            {"account_code": "2221", "account_name": tax_account_name, "debit": amount, "credit": Decimal("0.00")},
            {"account_code": bank_account_code, "debit": Decimal("0.00"), "credit": amount},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 3: Run API tests**

```powershell
python -m pytest backend/tests/test_tax_accounting_api.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py -v
```

Expected result: selected backend tests pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/tax_accounting.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_tax_accounting_api.py
git commit -m "feat: expose tax accounting api"
```

## Task 6: 前端税务核算面板和文档

**Files:**
- Create: `frontend/src/types/taxAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/TaxAccountingPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/taxAccountingApi.test.mjs`
- Create: `frontend/tests/taxAccountingPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Add frontend types and helpers**

```ts
export interface TaxFilingWorksheet {
  account_set_id: string;
  period: string;
  output_vat: string;
  input_vat: string;
  input_transfer_out: string;
  vat_payable: string;
  surtax_payable: string;
  income_tax_payable: string;
}
```

- [ ] **Step 2: Build panel**

Panel must show:
- 进项税额、销项税额、进项转出和应交增值税。
- 附加税测算。
- 所得税测算。
- 已计提和已缴纳状态。
- 申报底稿下载入口。

- [ ] **Step 3: Run regression**

```powershell
python -m pytest backend/tests/test_tax_accounting_service.py backend/tests/test_tax_accounting_api.py backend/tests/test_invoice_ocr_service.py backend/tests/test_period_close_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/types/taxAccounting.ts frontend/src/services/dashboardApi.ts frontend/src/components/TaxAccountingPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/taxAccountingApi.test.mjs frontend/tests/taxAccountingPanel.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: add tax accounting panel"
```

## 验收标准

- 可从正式分录生成增值税台账。
- 可计算应交增值税、附加税和企业所得税。
- 可生成未交增值税结转、附加税计提、所得税计提和纳税支付正式分录。
- 申报底稿能展示税基、税额、调整项和来源分录。
- 期间关闭后拒绝新增税务计提和缴款分录。
- 前端税务核算面板可读、可追溯、可审计。

## 风险控制

- 不接税局真实申报接口。
- 不声称完成发票验真或自动抵扣认证。
- 税额计算使用 `Decimal`。
- 申报底稿必须保留来源分录、发票号和人工调整记录。
- 所得税调整项必须记录调整原因和操作者。
