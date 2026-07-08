# Enterprise UX Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前功能堆叠式财务助手收敛为可日常使用的企业财务工作台，补齐首次启动、功能成熟度、设置配置和更新闭环。

**Architecture:** 后端新增本地应用配置服务，保存公司、账套、期间、首次启动和更新源设置。前端把单页长滚动体验改成工作区切换模型，首页聚焦今日待办，模块页统一显示成熟度和少量关键动作。更新中心通过配置 API 读写 manifest URL，并在下载软件包后提供原生更新器安装入口。

**Tech Stack:** FastAPI、Pydantic、JSON 配置文件、React、TypeScript、Ant Design、Node test runner、pytest。

## Global Constraints

- 始终使用简体中文界面文案、代码注释和文档。
- 不接入真实税局、银行、OCR 或发票验真服务。
- 不重写所有业务模块底层核算逻辑。
- 不引入新的 UI 框架，继续使用 React、TypeScript、Ant Design 和现有样式体系。
- 配置保存到用户数据目录，不写入源码目录。
- 更新源未配置时显示“未配置”，不作为错误处理。
- 软件本体安装动作必须调用 `ChinaFinanceUpdater.exe`，主程序不自我覆盖。

---

### Task 1: 本地应用配置 API

**Files:**
- Create: `backend/app/models/app_settings.py`
- Create: `backend/app/services/app_settings_service.py`
- Create: `backend/app/api/app_settings.py`
- Modify: `backend/app/api/router_registry.py`
- Test: `backend/tests/test_app_settings_api.py`

**Interfaces:**
- Produces: `AppSettings`
- Produces: `AppSettingsUpdate`
- Produces: `get_app_settings() -> AppSettings`
- Produces: `save_app_settings(update: AppSettingsUpdate) -> AppSettings`
- Produces: `GET /api/v1/app-settings`
- Produces: `PUT /api/v1/app-settings`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_app_settings_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_app_settings_api.py -q`

Expected: FAIL because `/api/v1/app-settings` does not exist.

- [ ] **Step 3: Implement models and service**

Implement `backend/app/models/app_settings.py`:

```python
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    company_name: str = "示例制造企业"
    default_account_set_id: str = "default"
    current_period: str = "2026-06"
    onboarding_completed: bool = False
    policy_manifest_url: str | None = None
    app_manifest_url: str | None = None


class AppSettingsUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1)
    default_account_set_id: str | None = Field(default=None, min_length=1)
    current_period: str | None = Field(default=None, min_length=7, max_length=7)
    onboarding_completed: bool | None = None
    policy_manifest_url: str | None = None
    app_manifest_url: str | None = None
```

Implement `backend/app/services/app_settings_service.py`:

```python
import json
from pathlib import Path

from app.models.app_settings import AppSettings, AppSettingsUpdate
from app.runtime_paths import get_user_data_dir


SETTINGS_FILENAME = "app-settings.json"


def get_app_settings_path() -> Path:
    return get_user_data_dir() / SETTINGS_FILENAME


def get_app_settings() -> AppSettings:
    path = get_app_settings_path()
    if not path.exists():
        settings = AppSettings()
        _write_settings(path, settings)
        return settings
    return AppSettings.model_validate_json(path.read_text(encoding="utf-8"))


def save_app_settings(update: AppSettingsUpdate) -> AppSettings:
    current = get_app_settings()
    data = current.model_dump()
    for key, value in update.model_dump(exclude_unset=True).items():
        data[key] = value
    settings = AppSettings.model_validate(data)
    _write_settings(get_app_settings_path(), settings)
    return settings


def _write_settings(path: Path, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

Implement `backend/app/api/app_settings.py`:

```python
from fastapi import APIRouter

from app.models.app_settings import AppSettings, AppSettingsUpdate
from app.services.app_settings_service import get_app_settings, save_app_settings


router = APIRouter(prefix="/api/v1/app-settings", tags=["app-settings"])


@router.get("", response_model=AppSettings)
def read_app_settings() -> AppSettings:
    return get_app_settings()


@router.put("", response_model=AppSettings)
def update_app_settings(update: AppSettingsUpdate) -> AppSettings:
    return save_app_settings(update)
```

Modify `backend/app/api/router_registry.py`:

```python
from app.api.app_settings import router as app_settings_router

# inside include_api_routers
app.include_router(app_settings_router)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest backend\tests\test_app_settings_api.py -q`

Expected: PASS.

---

### Task 2: 前端配置 API 与类型

**Files:**
- Create: `frontend/src/types/appSettings.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Test: `frontend/tests/appSettingsApi.test.mjs`

**Interfaces:**
- Consumes: `GET /api/v1/app-settings`
- Consumes: `PUT /api/v1/app-settings`
- Produces: `fetchAppSettings(apiBase?: string, fetcher?: typeof fetch)`
- Produces: `saveAppSettings(update, apiBase?: string, fetcher?: typeof fetch)`

- [ ] **Step 1: Write failing tests**

Create `frontend/tests/appSettingsApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const api = readFileSync(new URL("../src/services/dashboardApi.ts", import.meta.url), "utf8");

test("应用设置 API helper 读取和保存本地配置", () => {
  assert.match(api, /fetchAppSettings/);
  assert.match(api, /saveAppSettings/);
  assert.match(api, /\\/api\\/v1\\/app-settings/);
  assert.match(api, /PUT/);
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm --prefix frontend test`

Expected: FAIL because `fetchAppSettings` and `saveAppSettings` are missing.

- [ ] **Step 3: Implement frontend types and helpers**

Create `frontend/src/types/appSettings.ts`:

```typescript
export interface AppSettings {
  company_name: string;
  default_account_set_id: string;
  current_period: string;
  onboarding_completed: boolean;
  policy_manifest_url?: string | null;
  app_manifest_url?: string | null;
}

export type AppSettingsUpdate = Partial<AppSettings>;
```

Modify `frontend/src/services/dashboardApi.ts`:

```typescript
import type { AppSettings, AppSettingsUpdate } from "../types/appSettings";

export async function fetchAppSettings(apiBase = API_BASE, fetcher = fetch): Promise<AppSettings> {
  return fetchJson<AppSettings>(`${apiBase}/app-settings`, { fetcher });
}

export async function saveAppSettings(
  update: AppSettingsUpdate,
  apiBase = API_BASE,
  fetcher = fetch
): Promise<AppSettings> {
  return fetchJson<AppSettings>(`${apiBase}/app-settings`, {
    fetcher,
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update)
  });
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `npm --prefix frontend test`

Expected: PASS.

---

### Task 3: 工作区导航与成熟度标签

**Files:**
- Create: `frontend/src/workspaces/enterpriseWorkspaces.ts`
- Create: `frontend/src/components/CapabilityBadge.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/components/SaasModuleWorkspace.tsx`
- Test: `frontend/tests/enterpriseUxConsolidation.test.mjs`

**Interfaces:**
- Produces: `ENTERPRISE_WORKSPACES`
- Produces: `CapabilityBadge({ status })`
- Produces: `SaasModuleWorkspace.capabilityStatus`
- Produces: `DashboardLayout.activeWorkspace`

- [ ] **Step 1: Write failing tests**

Create `frontend/tests/enterpriseUxConsolidation.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const layout = readFileSync(new URL("../src/components/DashboardLayout.tsx", import.meta.url), "utf8");
const workspace = readFileSync(new URL("../src/workspaces/enterpriseWorkspaces.ts", import.meta.url), "utf8");
const badge = readFileSync(new URL("../src/components/CapabilityBadge.tsx", import.meta.url), "utf8");
const moduleShell = readFileSync(new URL("../src/components/SaasModuleWorkspace.tsx", import.meta.url), "utf8");

test("企业级体验收敛为六个一级工作区", () => {
  for (const label of ["工作台", "财务核算", "报表与分析", "税务与合规", "智能助手", "系统设置"]) {
    assert.ok(workspace.includes(label), `缺少工作区：${label}`);
    assert.ok(layout.includes(label), `主框架未接入工作区：${label}`);
  }
  assert.match(layout, /activeWorkspace/);
  assert.match(layout, /setActiveWorkspace/);
});

test("能力成熟度标签覆盖正式可用、演示数据、待配置和待接入", () => {
  for (const label of ["正式可用", "演示数据", "待配置", "待接入"]) {
    assert.ok(badge.includes(label), `缺少成熟度标签：${label}`);
  }
  assert.match(moduleShell, /CapabilityBadge/);
  assert.match(moduleShell, /capabilityStatus/);
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm --prefix frontend test`

Expected: FAIL because workspace model and badge are missing.

- [ ] **Step 3: Implement workspace model and badge**

Create `frontend/src/workspaces/enterpriseWorkspaces.ts`:

```typescript
export type CapabilityStatus = "ready" | "demo" | "needs_config" | "planned";

export interface EnterpriseWorkspace {
  key: string;
  label: string;
  description: string;
  primaryAnchors: string[];
  capabilityStatus: CapabilityStatus;
}

export const ENTERPRISE_WORKSPACES: EnterpriseWorkspace[] = [
  { key: "workbench", label: "工作台", description: "今日待办、风险和常用动作", primaryAnchors: ["ai-home"], capabilityStatus: "ready" },
  { key: "finance", label: "财务核算", description: "凭证、账簿、往来、银行、资产、薪酬、存货和月结", primaryAnchors: ["data-center"], capabilityStatus: "demo" },
  { key: "reports", label: "报表与分析", description: "报表生成、归档、合并和经营分析", primaryAnchors: ["statement-center"], capabilityStatus: "ready" },
  { key: "tax", label: "税务与合规", description: "税务台账、政策依据和风险闭环", primaryAnchors: ["tax-risk-center"], capabilityStatus: "needs_config" },
  { key: "assistant", label: "智能助手", description: "AI 问答、凭证草稿和自动审核", primaryAnchors: ["ai-advisor"], capabilityStatus: "demo" },
  { key: "settings", label: "系统设置", description: "公司、账套、期间、权限和更新中心", primaryAnchors: ["company-settings"], capabilityStatus: "ready" }
];
```

Create `frontend/src/components/CapabilityBadge.tsx`:

```typescript
import { Tag } from "antd";
import type { CapabilityStatus } from "../workspaces/enterpriseWorkspaces";

const STATUS_COPY: Record<CapabilityStatus, { color: string; label: string }> = {
  ready: { color: "green", label: "正式可用" },
  demo: { color: "blue", label: "演示数据" },
  needs_config: { color: "gold", label: "待配置" },
  planned: { color: "default", label: "待接入" }
};

export default function CapabilityBadge({ status }: { status: CapabilityStatus }) {
  const copy = STATUS_COPY[status];
  return <Tag color={copy.color}>{copy.label}</Tag>;
}
```

- [ ] **Step 4: Wire DashboardLayout and SaasModuleWorkspace**

Modify `SaasModuleWorkspaceProps`:

```typescript
capabilityStatus: CapabilityStatus;
compact?: boolean;
```

Render `<CapabilityBadge status={capabilityStatus} />` beside the module title.

Modify `DashboardLayout.tsx` to:

```typescript
const [activeWorkspace, setActiveWorkspace] = useState("workbench");
const handleWorkspaceChange = ({ key }: { key: string }) => setActiveWorkspace(key);
```

Use `ENTERPRISE_WORKSPACES` to build menu items with labels `"工作台"`, `"财务核算"`, `"报表与分析"`, `"税务与合规"`, `"智能助手"`, `"系统设置"`.

- [ ] **Step 5: Run tests to verify pass**

Run: `npm --prefix frontend test`

Expected: PASS.

---

### Task 4: 今日财务任务台首页

**Files:**
- Modify: `frontend/src/components/HomeDashboardPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/enterpriseUxConsolidation.test.mjs`

**Interfaces:**
- Produces: homepage copy `"今日财务任务台"`
- Produces: task labels `"待审核凭证"`, `"待对账流水"`, `"待归档文件"`, `"待月结检查"`, `"待复核风险"`

- [ ] **Step 1: Add failing homepage assertions**

Modify `frontend/tests/enterpriseUxConsolidation.test.mjs`:

```javascript
const home = readFileSync(new URL("../src/components/HomeDashboardPanel.tsx", import.meta.url), "utf8");

test("首页首屏改为今日财务任务台并减少说明噪音", () => {
  for (const label of ["今日财务任务台", "待审核凭证", "待对账流水", "待归档文件", "待月结检查", "待复核风险", "常用动作"]) {
    assert.ok(home.includes(label), `首页缺少：${label}`);
  }
  assert.ok(!home.includes("5秒财务状态"), "首页不再使用旧的 5 秒财务状态标题");
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm --prefix frontend test`

Expected: FAIL because homepage still uses old copy.

- [ ] **Step 3: Implement task-first home panel**

Modify `HomeDashboardPanel.tsx`:

```typescript
const todayTasks = [
  { label: "待审核凭证", value: "6", helper: "优先处理金额较大的采购和费用凭证" },
  { label: "待对账流水", value: "8", helper: "银行流水需要匹配正式资金分录" },
  { label: "待归档文件", value: "12", helper: "发票、回单和报表快照等待归档" },
  { label: "待月结检查", value: "3", helper: "固定资产折旧、税费计提、损益结转" },
  { label: "待复核风险", value: String(report.risk_count), helper: "税务和现金流风险需人工复核" }
];
```

Render these tasks before KPI cards, title the section `"今日财务任务台"` and include `"常用动作"` with existing data import and AI actions.

- [ ] **Step 4: Run tests to verify pass**

Run: `npm --prefix frontend test`

Expected: PASS.

---

### Task 5: 首次启动、设置和更新中心闭环

**Files:**
- Create: `frontend/src/components/OnboardingWizard.tsx`
- Modify: `frontend/src/components/UpdateCenterPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/services/dashboardApi.ts`
- Test: `frontend/tests/onboardingWizard.test.mjs`
- Test: `frontend/tests/updateCenterPanel.test.mjs`

**Interfaces:**
- Consumes: `fetchAppSettings`
- Consumes: `saveAppSettings`
- Produces: `OnboardingWizard`
- Produces: update center copy `"保存更新源"` and `"安装更新"`

- [ ] **Step 1: Write failing tests**

Create `frontend/tests/onboardingWizard.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const wizard = readFileSync(new URL("../src/components/OnboardingWizard.tsx", import.meta.url), "utf8");
const layout = readFileSync(new URL("../src/components/DashboardLayout.tsx", import.meta.url), "utf8");

test("首次启动向导覆盖公司、账套、期间、数据模式和更新配置", () => {
  for (const label of ["首次启动向导", "公司信息", "账套与期间", "数据模式", "更新配置", "进入工作台"]) {
    assert.ok(wizard.includes(label), `缺少向导文案：${label}`);
  }
  assert.match(layout, /OnboardingWizard/);
  assert.match(layout, /fetchAppSettings/);
  assert.match(layout, /saveAppSettings/);
});
```

Modify `frontend/tests/updateCenterPanel.test.mjs`:

```javascript
assert.match(panel, /保存更新源/);
assert.match(panel, /安装更新/);
assert.match(panel, /saveAppSettings/);
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm --prefix frontend test`

Expected: FAIL because wizard and update source editing are missing.

- [ ] **Step 3: Implement onboarding wizard**

Create `frontend/src/components/OnboardingWizard.tsx` with an Ant Design `Modal`, `Steps`, `Input`, `Switch`, and final `"进入工作台"` button. On finish call:

```typescript
onFinish({
  company_name: companyName,
  default_account_set_id: accountSetId,
  current_period: currentPeriod,
  onboarding_completed: true,
  policy_manifest_url: policyManifestUrl || null,
  app_manifest_url: appManifestUrl || null
});
```

- [ ] **Step 4: Wire settings into DashboardLayout**

In `DashboardLayout.tsx`, load settings on mount:

```typescript
const [settings, setSettings] = useState<AppSettings | null>(null);
const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);

useEffect(() => {
  fetchAppSettings().then((next) => {
    setSettings(next);
    setIsOnboardingOpen(!next.onboarding_completed);
  });
}, []);
```

Render `OnboardingWizard open={isOnboardingOpen}` and pass `saveAppSettings`.

- [ ] **Step 5: Update UpdateCenterPanel**

Add policy and app manifest inputs. Save them through `saveAppSettings`. Show `"安装更新"` when `lastAppResult?.package_path` or status contains a downloaded app update package path. The first implementation may open a copyable command or show a message explaining that installation will call the bundled updater after closing the app.

- [ ] **Step 6: Run tests to verify pass**

Run: `npm --prefix frontend test`

Expected: PASS.

---

### Task 6: Final verification

**Files:**
- Verify all changed files.

**Interfaces:**
- Consumes all tasks above.
- Produces verified enterprise UX consolidation build.

- [ ] **Step 1: Run backend tests**

Run: `python -m pytest backend\tests -q`

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run: `npm --prefix frontend test`

Expected: PASS.

- [ ] **Step 3: Run production build**

Run: `npm --prefix frontend run build`

Expected: PASS. Vite chunk-size warning is acceptable.

- [ ] **Step 4: Run diff whitespace check**

Run: `git diff --check`

Expected: no output.

- [ ] **Step 5: Browser verification**

Open `http://127.0.0.1:5173` or the installed desktop URL and verify:

- 首页首屏显示 `"今日财务任务台"`。
- 左侧导航显示 6 个一级工作区。
- 点击 `"数据分析"` 的旧入口不再是主路径；新 `"财务核算"` 工作区稳定显示财务核算内容。
- `"系统设置"` 显示首次启动、更新源和更新中心。
- 未配置更新源显示 `"待配置"` 或 `"未配置"`。

Expected: screenshots show cleaner, task-first layout without wrong anchor landing.

## Self-Review

- Spec coverage: local config, workspace navigation, maturity tags, onboarding, update source config, update install entry, navigation stability, tests and visual verification all map to tasks.
- Placeholder scan: no placeholder directives are present.
- Type consistency: `CapabilityStatus`, `AppSettings`, `AppSettingsUpdate`, `fetchAppSettings`, `saveAppSettings`, and `OnboardingWizard` names are consistent across tasks.
