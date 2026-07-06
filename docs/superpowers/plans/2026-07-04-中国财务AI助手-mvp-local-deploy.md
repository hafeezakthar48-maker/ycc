# China Finance AI Assistant MVP Local Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个本地可运行的 China Finance AI Assistant MVP，打开后直接进入经营分析驾驶舱，展示示例财务数据、图表、风险预警和经营分析报告草稿。

**Architecture:** 新项目独立放在 `D:\codex-project\中国财务AI助手`，不改动现有 `EngineeringCadAi` 代码。后端使用 FastAPI 提供示例数据、指标、风险和报告 API；前端使用 React、Vite、ECharts 消费 API 并展示管理驾驶舱。

**Tech Stack:** Python 3.14、FastAPI、Pydantic、pytest、React、TypeScript、Vite、ECharts、PowerShell 本地启动脚本。

**Execution Constraint:** 用户已明确要求跳过 Git。本计划不执行 `git commit`、`git push`、分支创建或 PR 操作；验收以本地测试、构建和可访问 URL 为准。

---

## File Structure

Create:

```text
D:\codex-project\中国财务AI助手\
  README.md
  start-local.ps1
  backend\
    pyproject.toml
    app\
      __init__.py
      main.py
      api\
        __init__.py
        dashboard.py
      data\
        __init__.py
        sample_finance_data.py
      models\
        __init__.py
        finance.py
      services\
        __init__.py
        analysis_service.py
        risk_service.py
        report_service.py
    tests\
      test_analysis_service.py
      test_risk_service.py
      test_dashboard_api.py
  frontend\
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    src\
      main.tsx
      App.tsx
      styles.css
      components\
        DashboardLayout.tsx
        MetricCard.tsx
        RiskPanel.tsx
        ReportPanel.tsx
      charts\
        TrendChart.tsx
        ExpensePieChart.tsx
        CashFlowChart.tsx
        ProfitWaterfallChart.tsx
        RiskHeatmap.tsx
      services\
        dashboardApi.ts
      types\
        dashboard.ts
  docs\
    00-product-vision.md
    01-mvp-design.md
    02-api-design.md
```

Modify:

```text
D:\codex-project\.gitignore
```

Add these entries if missing:

```text
中国财务AI助手/backend/.venv/
中国财务AI助手/frontend/node_modules/
中国财务AI助手/frontend/dist/
```

## Task 1: Create Independent Project Skeleton

**Files:**
- Create: `D:\codex-project\中国财务AI助手\README.md`
- Create: all empty package marker files listed in File Structure
- Modify: `D:\codex-project\.gitignore`

- [ ] **Step 1: Create directories**

Run:

```powershell
New-Item -ItemType Directory -Force `
  -Path `
    'D:\codex-project\中国财务AI助手\backend\app\api', `
    'D:\codex-project\中国财务AI助手\backend\app\data', `
    'D:\codex-project\中国财务AI助手\backend\app\models', `
    'D:\codex-project\中国财务AI助手\backend\app\services', `
    'D:\codex-project\中国财务AI助手\backend\tests', `
    'D:\codex-project\中国财务AI助手\frontend\src\components', `
    'D:\codex-project\中国财务AI助手\frontend\src\charts', `
    'D:\codex-project\中国财务AI助手\frontend\src\services', `
    'D:\codex-project\中国财务AI助手\frontend\src\types', `
    'D:\codex-project\中国财务AI助手\docs'
```

Expected: directories exist and existing `EngineeringCadAi` files are unchanged.

- [ ] **Step 2: Create README**

Create `D:\codex-project\中国财务AI助手\README.md`:

```markdown
# China Finance AI Assistant

面向中国企业财务经理的经营分析与风险预警驾驶舱 MVP。

第一版使用内置示例财务数据，支持：

- 经营总览
- 利润、收入、成本趋势分析
- 费用结构分析
- 现金流分析
- 风险预警
- AI 经营分析报告草稿

第一版不做真实 Excel 上传、OCR、自动记账、自动申报税务或真实法规库检索。
```

- [ ] **Step 3: Add package markers**

Create empty files:

```text
D:\codex-project\中国财务AI助手\backend\app\__init__.py
D:\codex-project\中国财务AI助手\backend\app\api\__init__.py
D:\codex-project\中国财务AI助手\backend\app\data\__init__.py
D:\codex-project\中国财务AI助手\backend\app\models\__init__.py
D:\codex-project\中国财务AI助手\backend\app\services\__init__.py
```

- [ ] **Step 4: Update ignore rules**

Ensure `D:\codex-project\.gitignore` contains:

```text
中国财务AI助手/backend/.venv/
中国财务AI助手/frontend/node_modules/
中国财务AI助手/frontend/dist/
```

- [ ] **Step 5: Verify skeleton**

Run:

```powershell
Test-Path 'D:\codex-project\中国财务AI助手\backend\app\main.py'
Test-Path 'D:\codex-project\中国财务AI助手\frontend\src'
```

Expected: first command may be `False` until Task 4, second command is `True`.

## Task 2: Define Backend Models And Sample Data

**Files:**
- Create: `D:\codex-project\中国财务AI助手\backend\pyproject.toml`
- Create: `D:\codex-project\中国财务AI助手\backend\app\models\finance.py`
- Create: `D:\codex-project\中国财务AI助手\backend\app\data\sample_finance_data.py`
- Test: `D:\codex-project\中国财务AI助手\backend\tests\test_analysis_service.py`

- [ ] **Step 1: Create backend project config**

Create `backend\pyproject.toml`:

```toml
[project]
name = "china-finance-ai-assistant-backend"
version = "0.1.0"
description = "China Finance AI Assistant MVP backend"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.116.0",
  "uvicorn[standard]>=0.35.0",
  "pydantic>=2.11.0"
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28.0",
  "pytest>=8.4.0"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Write finance models**

Create `backend\app\models\finance.py`:

```python
from pydantic import BaseModel, Field


class MonthlyFinanceRecord(BaseModel):
    period: str
    revenue: float
    cost: float
    sales_expense: float
    admin_expense: float
    rd_expense: float
    finance_expense: float
    total_profit: float
    net_profit: float
    cash: float
    accounts_receivable: float
    inventory: float
    fixed_assets: float
    total_assets: float
    short_term_loans: float
    accounts_payable: float
    total_liabilities: float
    owner_equity: float
    operating_cash_inflow: float
    operating_cash_outflow: float
    operating_cash_flow_net: float
    investing_cash_flow_net: float
    financing_cash_flow_net: float
    customer_collection: float
    sales_orders: float
    purchase_amount: float
    inventory_turnover_days: float
    tax_burden_rate: float


class MetricCard(BaseModel):
    key: str
    title: str
    value: str
    change: str
    status: str = "normal"


class ChartPoint(BaseModel):
    period: str
    value: float


class TrendChartSeries(BaseModel):
    name: str
    data: list[ChartPoint]


class RiskItem(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=5)
    level_label: str
    description: str
    trigger_reason: str
    suggested_checks: list[str]
    compliance_note: str


class DashboardOverview(BaseModel):
    period: str
    company_name: str
    metrics: list[MetricCard]
    trend_series: list[TrendChartSeries]
    expense_structure: list[ChartPoint]
    cash_flow_series: list[TrendChartSeries]
    profit_waterfall: list[ChartPoint]
    risk_heatmap: list[list[int]]
    risks: list[RiskItem]
    ai_summary: str


class ReportSection(BaseModel):
    title: str
    content: str


class ManagementReport(BaseModel):
    period: str
    company_name: str
    title: str
    sections: list[ReportSection]
```

- [ ] **Step 3: Write sample data**

Create `backend\app\data\sample_finance_data.py` with 12 records from `2025-07` to `2026-06`. Ensure `2026-06` has revenue `1286`, net profit `146`, operating cash flow net `92`, inventory turnover days `74`, and tax burden rate `0.038` so the dashboard can trigger cash flow, inventory and tax burden review prompts.

- [ ] **Step 4: Write initial failing analysis test**

Create `backend\tests\test_analysis_service.py`:

```python
from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.analysis_service import build_dashboard_overview


def test_dashboard_overview_contains_core_metrics():
    overview = build_dashboard_overview("2026-06", SAMPLE_FINANCE_DATA)

    titles = {metric.title for metric in overview.metrics}

    assert overview.period == "2026-06"
    assert "营业收入" in titles
    assert "净利润" in titles
    assert "经营现金流" in titles
    assert "综合风险" in titles
```

- [ ] **Step 5: Run failing test**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\backend
python -m pytest tests\test_analysis_service.py -q
```

Expected: FAIL because `app.services.analysis_service` does not exist yet.

## Task 3: Implement Analysis And Risk Services

**Files:**
- Create: `D:\codex-project\中国财务AI助手\backend\app\services\analysis_service.py`
- Create: `D:\codex-project\中国财务AI助手\backend\app\services\risk_service.py`
- Test: `D:\codex-project\中国财务AI助手\backend\tests\test_analysis_service.py`
- Test: `D:\codex-project\中国财务AI助手\backend\tests\test_risk_service.py`

- [ ] **Step 1: Write risk service test**

Create `backend\tests\test_risk_service.py`:

```python
from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.risk_service import detect_risks


def test_detect_risks_returns_prudent_finance_risk_items():
    risks = detect_risks("2026-06", SAMPLE_FINANCE_DATA)

    titles = {risk.title for risk in risks}

    assert "现金流与利润背离" in titles
    assert "库存周转异常" in titles
    assert "税负率需复核" in titles
    assert all("建议财务人员结合企业实际业务" in risk.compliance_note for risk in risks)
```

- [ ] **Step 2: Implement risk service**

Create `backend\app\services\risk_service.py`:

```python
from app.models.finance import MonthlyFinanceRecord, RiskItem


COMPLIANCE_NOTE = "建议财务人员结合企业实际业务、申报口径和最新政策进一步复核。"


def _find_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord:
    for record in records:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in records)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _risk_level_label(level: int) -> str:
    labels = {
        1: "低风险",
        2: "关注",
        3: "需复核",
        4: "高风险",
        5: "严重风险",
    }
    return labels[level]


def detect_risks(period: str, records: list[MonthlyFinanceRecord]) -> list[RiskItem]:
    current = _find_record(period, records)
    risks: list[RiskItem] = []

    expense_rate = (
        current.sales_expense + current.admin_expense + current.rd_expense + current.finance_expense
    ) / current.revenue
    cash_profit_ratio = current.operating_cash_flow_net / current.net_profit if current.net_profit else 0
    gross_margin = (current.revenue - current.cost) / current.revenue

    if expense_rate >= 0.14:
        risks.append(RiskItem(
            id="expense-rate-review",
            title="费用率异常",
            level=3,
            level_label=_risk_level_label(3),
            description="本期期间费用率处于较高水平，可能压缩经营利润。",
            trigger_reason=f"期间费用率为 {expense_rate:.1%}，达到需复核阈值。",
            suggested_checks=["销售费用明细", "管理费用审批记录", "研发费用归集口径"],
            compliance_note=COMPLIANCE_NOTE,
        ))

    if cash_profit_ratio < 0.8:
        risks.append(RiskItem(
            id="cash-profit-divergence",
            title="现金流与利润背离",
            level=4,
            level_label=_risk_level_label(4),
            description="经营现金流净额低于净利润，利润质量需要进一步复核。",
            trigger_reason=f"经营现金流/净利润为 {cash_profit_ratio:.1%}，低于 80%。",
            suggested_checks=["应收账款账龄表", "期后回款记录", "大额客户信用政策"],
            compliance_note=COMPLIANCE_NOTE,
        ))

    if current.inventory_turnover_days >= 70:
        risks.append(RiskItem(
            id="inventory-turnover-review",
            title="库存周转异常",
            level=3,
            level_label=_risk_level_label(3),
            description="库存周转天数偏长，可能影响资金占用和存货跌价风险。",
            trigger_reason=f"库存周转天数为 {current.inventory_turnover_days:.0f} 天。",
            suggested_checks=["库存库龄表", "滞销品清单", "存货跌价准备测算表"],
            compliance_note=COMPLIANCE_NOTE,
        ))

    if current.tax_burden_rate < 0.04:
        risks.append(RiskItem(
            id="tax-burden-review",
            title="税负率需复核",
            level=3,
            level_label=_risk_level_label(3),
            description="税负率低于示例行业观察区间，建议复核申报口径。",
            trigger_reason=f"税负率为 {current.tax_burden_rate:.1%}。",
            suggested_checks=["增值税申报表", "企业所得税预缴申报表", "收入确认与发票开具匹配表"],
            compliance_note=COMPLIANCE_NOTE,
        ))

    if gross_margin < 0.2:
        risks.append(RiskItem(
            id="gross-margin-review",
            title="毛利率异常",
            level=3,
            level_label=_risk_level_label(3),
            description="毛利率低于经营观察阈值，建议复核成本结转。",
            trigger_reason=f"毛利率为 {gross_margin:.1%}。",
            suggested_checks=["主营业务成本明细", "采购价格变动表", "成本结转凭证"],
            compliance_note=COMPLIANCE_NOTE,
        ))

    return risks
```

- [ ] **Step 3: Implement analysis service**

Create `backend\app\services\analysis_service.py`:

```python
from app.models.finance import ChartPoint, DashboardOverview, MetricCard, MonthlyFinanceRecord, TrendChartSeries
from app.services.risk_service import detect_risks


COMPANY_NAME = "示例制造企业"


def _find_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord:
    for record in records:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in records)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _previous_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord | None:
    for index, record in enumerate(records):
        if record.period == period and index > 0:
            return records[index - 1]
    return None


def _format_money(value: float) -> str:
    return f"¥{value:,.0f}万"


def _format_rate(value: float) -> str:
    return f"{value:.1%}"


def _change_text(current: float, previous: float | None) -> str:
    if previous is None or previous == 0:
        return "无上期数据"
    change = current / previous - 1
    prefix = "+" if change >= 0 else ""
    return f"环比 {prefix}{change:.1%}"


def build_dashboard_overview(period: str, records: list[MonthlyFinanceRecord]) -> DashboardOverview:
    current = _find_record(period, records)
    previous = _previous_record(period, records)
    risks = detect_risks(period, records)
    total_expense = current.sales_expense + current.admin_expense + current.rd_expense + current.finance_expense
    gross_profit = current.revenue - current.cost

    metrics = [
        MetricCard(
            key="revenue",
            title="营业收入",
            value=_format_money(current.revenue),
            change=_change_text(current.revenue, previous.revenue if previous else None),
        ),
        MetricCard(
            key="netProfit",
            title="净利润",
            value=_format_money(current.net_profit),
            change=_change_text(current.net_profit, previous.net_profit if previous else None),
        ),
        MetricCard(
            key="operatingCashFlow",
            title="经营现金流",
            value=_format_money(current.operating_cash_flow_net),
            change=_change_text(current.operating_cash_flow_net, previous.operating_cash_flow_net if previous else None),
            status="warning" if current.operating_cash_flow_net < current.net_profit else "normal",
        ),
        MetricCard(
            key="risk",
            title="综合风险",
            value="★★★★☆" if any(risk.level >= 4 for risk in risks) else "★★★☆☆",
            change="需财务复核" if risks else "低风险",
            status="danger" if any(risk.level >= 4 for risk in risks) else "warning",
        ),
    ]

    trend_series = [
        TrendChartSeries(name="营业收入", data=[ChartPoint(period=item.period, value=item.revenue) for item in records]),
        TrendChartSeries(name="营业成本", data=[ChartPoint(period=item.period, value=item.cost) for item in records]),
        TrendChartSeries(name="净利润", data=[ChartPoint(period=item.period, value=item.net_profit) for item in records]),
    ]

    cash_flow_series = [
        TrendChartSeries(name="经营现金流", data=[ChartPoint(period=item.period, value=item.operating_cash_flow_net) for item in records]),
        TrendChartSeries(name="投资现金流", data=[ChartPoint(period=item.period, value=item.investing_cash_flow_net) for item in records]),
        TrendChartSeries(name="筹资现金流", data=[ChartPoint(period=item.period, value=item.financing_cash_flow_net) for item in records]),
    ]

    ai_summary = (
        f"{COMPANY_NAME}在{period}实现营业收入{_format_money(current.revenue)}，净利润{_format_money(current.net_profit)}。"
        f"经营现金流为{_format_money(current.operating_cash_flow_net)}，低于净利润时应重点复核回款质量。"
        "系统识别出的风险仅作为经营与财税复核提示，不替代财务负责人判断。"
    )

    return DashboardOverview(
        period=period,
        company_name=COMPANY_NAME,
        metrics=metrics,
        trend_series=trend_series,
        expense_structure=[
            ChartPoint(period="销售费用", value=current.sales_expense),
            ChartPoint(period="管理费用", value=current.admin_expense),
            ChartPoint(period="研发费用", value=current.rd_expense),
            ChartPoint(period="财务费用", value=current.finance_expense),
        ],
        cash_flow_series=cash_flow_series,
        profit_waterfall=[
            ChartPoint(period="营业收入", value=current.revenue),
            ChartPoint(period="营业成本", value=-current.cost),
            ChartPoint(period="毛利", value=gross_profit),
            ChartPoint(period="期间费用", value=-total_expense),
            ChartPoint(period="净利润", value=current.net_profit),
        ],
        risk_heatmap=[
            [1, 2, 3, 4],
            [2, 3, 3, 4],
            [1, 2, 3, 3],
        ],
        risks=risks,
        ai_summary=ai_summary,
    )
```

- [ ] **Step 4: Run service tests**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\backend
python -m pytest tests\test_analysis_service.py tests\test_risk_service.py -q
```

Expected: PASS.

## Task 4: Implement Report Service And FastAPI Routes

**Files:**
- Create: `D:\codex-project\中国财务AI助手\backend\app\services\report_service.py`
- Create: `D:\codex-project\中国财务AI助手\backend\app\api\dashboard.py`
- Create: `D:\codex-project\中国财务AI助手\backend\app\main.py`
- Test: `D:\codex-project\中国财务AI助手\backend\tests\test_dashboard_api.py`

- [ ] **Step 1: Write API tests**

Create `backend\tests\test_dashboard_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_endpoint_returns_dashboard_payload():
    response = client.get("/api/v1/dashboard/overview?period=2026-06")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["metrics"]
    assert payload["trend_series"]
    assert payload["risks"]


def test_unknown_period_returns_404():
    response = client.get("/api/v1/dashboard/overview?period=2030-01")

    assert response.status_code == 404
    assert "可用期间" in response.json()["detail"]


def test_report_endpoint_contains_required_sections():
    response = client.get("/api/v1/dashboard/report?period=2026-06")

    assert response.status_code == 200
    titles = {section["title"] for section in response.json()["sections"]}
    assert {"利润分析", "资金分析", "风险提示", "管理建议"}.issubset(titles)
```

- [ ] **Step 2: Implement report service**

Create `backend\app\services\report_service.py`:

```python
from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import ManagementReport, ReportSection
from app.services.analysis_service import COMPANY_NAME, build_dashboard_overview


def build_management_report(period: str) -> ManagementReport:
    overview = build_dashboard_overview(period, SAMPLE_FINANCE_DATA)
    risk_titles = "、".join(risk.title for risk in overview.risks) if overview.risks else "未发现需重点复核事项"

    return ManagementReport(
        period=period,
        company_name=COMPANY_NAME,
        title=f"{COMPANY_NAME}{period}经营分析报告草稿",
        sections=[
            ReportSection(
                title="利润分析",
                content="本期收入、成本和净利润保持增长，但期间费用率需要结合预算和业务扩张情况复核。",
            ),
            ReportSection(
                title="资金分析",
                content="经营现金流低于净利润，建议关注应收账款期后回款、客户信用政策和现金流预测。",
            ),
            ReportSection(
                title="风险提示",
                content=f"系统识别的重点复核事项包括：{risk_titles}。这些内容仅作为经营与财税风险提示。",
            ),
            ReportSection(
                title="管理建议",
                content="建议财务经理组织销售、采购、仓储和税务岗位复核费用、回款、库存和申报口径。",
            ),
        ],
    )
```

- [ ] **Step 3: Implement dashboard routes**

Create `backend\app\api\dashboard.py`:

```python
import re

from fastapi import APIRouter, HTTPException, Query

from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.analysis_service import build_dashboard_overview
from app.services.report_service import build_management_report
from app.services.risk_service import detect_risks


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _validate_period(period: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise HTTPException(status_code=422, detail="period 格式必须为 YYYY-MM")


def _to_http_error(error: ValueError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


@router.get("/overview")
def get_overview(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return build_dashboard_overview(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.get("/risks")
def get_risks(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return detect_risks(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.get("/report")
def get_report(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return build_management_report(period)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.get("/sample-data")
def get_sample_data():
    return SAMPLE_FINANCE_DATA
```

- [ ] **Step 4: Implement FastAPI app**

Create `backend\app\main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router


app = FastAPI(title="China Finance AI Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run backend API tests**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\backend
python -m pytest -q
```

Expected: PASS.

## Task 5: Create React/ECharts Frontend

**Files:**
- Create: `D:\codex-project\中国财务AI助手\frontend\package.json`
- Create: `D:\codex-project\中国财务AI助手\frontend\index.html`
- Create: `D:\codex-project\中国财务AI助手\frontend\tsconfig.json`
- Create: `D:\codex-project\中国财务AI助手\frontend\vite.config.ts`
- Create: `D:\codex-project\中国财务AI助手\frontend\src\types\dashboard.ts`
- Create: `D:\codex-project\中国财务AI助手\frontend\src\services\dashboardApi.ts`
- Create: React component and chart files listed in File Structure

- [ ] **Step 1: Create package config**

Create `frontend\package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "preview": "vite preview --host 127.0.0.1"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "echarts": "^5.6.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "vite": "^6.0.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 2: Create dashboard types**

Create `frontend\src\types\dashboard.ts`:

```typescript
export interface MetricCard {
  key: string;
  title: string;
  value: string;
  change: string;
  status: "normal" | "warning" | "danger";
}

export interface ChartPoint {
  period: string;
  value: number;
}

export interface TrendChartSeries {
  name: string;
  data: ChartPoint[];
}

export interface RiskItem {
  id: string;
  title: string;
  level: number;
  level_label: string;
  description: string;
  trigger_reason: string;
  suggested_checks: string[];
  compliance_note: string;
}

export interface DashboardOverview {
  period: string;
  company_name: string;
  metrics: MetricCard[];
  trend_series: TrendChartSeries[];
  expense_structure: ChartPoint[];
  cash_flow_series: TrendChartSeries[];
  profit_waterfall: ChartPoint[];
  risk_heatmap: number[][];
  risks: RiskItem[];
  ai_summary: string;
}

export interface ManagementReport {
  period: string;
  company_name: string;
  title: string;
  sections: Array<{ title: string; content: string }>;
}
```

- [ ] **Step 3: Create API client**

Create `frontend\src\services\dashboardApi.ts`:

```typescript
import type { DashboardOverview, ManagementReport } from "../types/dashboard";

const API_BASE = "http://127.0.0.1:8000";

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchOverview(period: string): Promise<DashboardOverview> {
  return requestJson<DashboardOverview>(`/api/v1/dashboard/overview?period=${period}`);
}

export function fetchReport(period: string): Promise<ManagementReport> {
  return requestJson<ManagementReport>(`/api/v1/dashboard/report?period=${period}`);
}
```

- [ ] **Step 4: Create React app**

Create `frontend\src\App.tsx` that loads `fetchOverview("2026-06")` and `fetchReport("2026-06")`, displays loading and error states, then renders `DashboardLayout`.

- [ ] **Step 5: Create charts**

Use ECharts inside each chart component. Each component must initialize a chart in `useEffect`, call `chart.setOption(...)`, listen for `resize`, and dispose on unmount.

Required chart components:

```text
TrendChart.tsx
ExpensePieChart.tsx
CashFlowChart.tsx
ProfitWaterfallChart.tsx
RiskHeatmap.tsx
```

- [ ] **Step 6: Create dashboard layout**

Create `DashboardLayout.tsx` with:

```text
顶部栏：China Finance AI Assistant、示例制造企业、期间 2026-06、生成报告按钮
左侧导航：经营总览、利润分析、现金流分析、风险预警、AI 报告
主区域：指标卡、趋势图、费用图、现金流图、风险面板、AI 摘要、报告草稿
```

- [ ] **Step 7: Create CSS**

Create `frontend\src\styles.css` with a professional dashboard style:

```text
white background panels
8px or smaller border radius
clear grid layout
responsive single-column mobile layout
no marketing hero page
no decorative gradient orbs
```

- [ ] **Step 8: Build frontend**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\frontend
npm install
npm run build
```

Expected: build succeeds and `frontend\dist` exists.

## Task 6: Local Startup Script And Deployment Verification

**Files:**
- Create: `D:\codex-project\中国财务AI助手\start-local.ps1`
- Modify: `D:\codex-project\中国财务AI助手\README.md`

- [ ] **Step 1: Create local startup script**

Create `start-local.ps1`:

```powershell
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = "C:\Python314\python.exe"

if (-not (Test-Path (Join-Path $backend ".venv"))) {
  & $python -m venv (Join-Path $backend ".venv")
}

$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "$backend[dev]"

Push-Location $frontend
if (-not (Test-Path "node_modules")) {
  npm install
}
Pop-Location

Start-Process -WindowStyle Hidden -FilePath $venvPython -ArgumentList @(
  "-m", "uvicorn", "app.main:app",
  "--host", "127.0.0.1",
  "--port", "8000",
  "--app-dir", $backend
)

Start-Process -WindowStyle Hidden -FilePath "npm" -ArgumentList @(
  "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"
) -WorkingDirectory $frontend

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "后端：http://127.0.0.1:8000/health"
Write-Host "前端：http://127.0.0.1:5173"
```

- [ ] **Step 2: Run backend tests**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd D:\codex-project\中国财务AI助手\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Start local deployment**

Run:

```powershell
cd D:\codex-project\中国财务AI助手
.\start-local.ps1
```

Expected:

```text
后端：http://127.0.0.1:8000/health
前端：http://127.0.0.1:5173
```

- [ ] **Step 5: Verify API**

Run:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/v1/dashboard/overview?period=2026-06"
```

Expected: both return HTTP 200.

- [ ] **Step 6: Verify UI with browser**

Open:

```text
http://127.0.0.1:5173
```

Verify:

- Desktop viewport shows metric cards, trend chart, expense chart, cash flow chart, risk heatmap and report draft.
- Mobile viewport has no overlapping text and charts are visible.
- No blank chart canvas appears after refresh.

## Self-Review Checklist

- Spec coverage: tasks cover independent project directory, backend API, sample data, metrics, risk rules, report draft, React/ECharts dashboard and local startup.
- Scope boundary: plan does not include real Excel upload, OCR, automatic bookkeeping, automatic tax filing, daily policy sync or real regulation retrieval.
- Git constraint: plan contains no Git commit, branch, push or PR step.
- Compliance wording: risk service uses prudent review language and does not assert confirmed violation.
- Type consistency: backend model names map to frontend TypeScript interfaces and chart inputs.

