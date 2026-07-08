# 月度联网政策库自动更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让独立桌面版财务助手在每月 1 号自动联网检查并更新法规、税率、政策数据包，同时保留手动检查、审计日志和失败回滚。

**Architecture:** 前端仍只访问本机 `127.0.0.1:8000`。新增 FastAPI 更新中心接口，后端服务负责读取本机配置、判断月度计划、下载远端更新清单、校验 SHA256、保存数据包版本与更新日志。自动调度放在桌面后端线程内启动，不依赖 PowerShell、Node.js 或外部常驻进程。

**Tech Stack:** FastAPI、Pydantic、Python 标准库 `urllib.request`、本机 JSON 状态文件、React/Ant Design。

## Global Constraints

- 始终用简体中文文档和注释。
- 目标电脑不需要 Python、Node.js、npm 或 PowerShell 脚本依赖。
- 自动更新仅访问 HTTPS 源，默认不上传企业财务数据。
- 每月 1 号自动检查一次；当天已成功或失败记录后不重复刷屏。
- 下载结果必须先校验 SHA256，再更新本地状态。
- 失败不能影响当前软件启动和离线使用。

---

### Task 1: 更新中心后端模型与状态文件

**Files:**
- Create: `backend/app/models/update_center.py`
- Create: `backend/app/services/update_center_service.py`
- Test: `backend/tests/test_update_center_service.py`

**Interfaces:**
- Produces: `UpdateCenterConfig`、`UpdateCenterStatus`、`UpdateCheckResult`
- Produces: `get_update_status(now: datetime | None = None) -> UpdateCenterStatus`
- Produces: `should_run_monthly_update(status: UpdateCenterStatus, now: datetime) -> bool`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime

from app.services.update_center_service import get_update_status, should_run_monthly_update


def test_monthly_auto_update_runs_on_first_day_when_not_checked(tmp_path, monkeypatch):
    monkeypatch.setenv("CHINA_FINANCE_AI_DATA_DIR", str(tmp_path))
    status = get_update_status(now=datetime(2026, 8, 1, 9, 0, 0))

    assert status.config.auto_update_enabled is True
    assert status.config.schedule_day == 1
    assert should_run_monthly_update(status, datetime(2026, 8, 1, 9, 0, 0)) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend\tests\test_update_center_service.py::test_monthly_auto_update_runs_on_first_day_when_not_checked -q`

Expected: FAIL because `app.services.update_center_service` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement Pydantic models and JSON-backed default status under `get_user_data_dir() / "update-center.json"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend\tests\test_update_center_service.py -q`

Expected: PASS.

### Task 2: 联网清单下载、SHA256 校验和更新记录

**Files:**
- Modify: `backend/app/services/update_center_service.py`
- Test: `backend/tests/test_update_center_service.py`

**Interfaces:**
- Produces: `check_for_updates(fetch_bytes: Callable[[str], bytes] | None = None, now: datetime | None = None) -> UpdateCheckResult`
- Consumes: `UpdateCenterStatus`

- [ ] **Step 1: Write the failing test**

```python
import hashlib
import json
from datetime import datetime

from app.services.update_center_service import check_for_updates


def test_check_for_updates_accepts_https_manifest_and_records_version(tmp_path, monkeypatch):
    monkeypatch.setenv("CHINA_FINANCE_AI_DATA_DIR", str(tmp_path))
    package = b'{"documents":[]}'
    manifest = {
        "version": "2026.08",
        "published_at": "2026-08-01T00:00:00+08:00",
        "package_url": "https://updates.example.test/policy-2026-08.json",
        "sha256": hashlib.sha256(package).hexdigest(),
        "summary": "2026年8月法规政策包"
    }

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("manifest.json"):
            return json.dumps(manifest).encode("utf-8")
        return package

    result = check_for_updates(fetch_bytes=fetch_bytes, now=datetime(2026, 8, 1, 9, 0, 0))

    assert result.status == "updated"
    assert result.current_policy_version == "2026.08"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend\tests\test_update_center_service.py::test_check_for_updates_accepts_https_manifest_and_records_version -q`

Expected: FAIL because `check_for_updates` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Download manifest and package through injected fetcher, require HTTPS URL, verify package SHA256, persist version and event log.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend\tests\test_update_center_service.py -q`

Expected: PASS.

### Task 3: API 与桌面月度调度

**Files:**
- Create: `backend/app/api/update_center.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/desktop.py`
- Test: `backend/tests/test_update_center_api.py`
- Test: `backend/tests/test_desktop_entrypoint.py`

**Interfaces:**
- Produces: `GET /api/v1/update-center/status`
- Produces: `POST /api/v1/update-center/check`
- Produces: `start_monthly_update_worker(...) -> threading.Thread`

- [ ] **Step 1: Write failing API and worker tests**

Test status endpoint returns `auto_update_enabled=True` and manual check endpoint returns an update result. Test desktop server starts the monthly worker unless `--server-only` is used.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_update_center_api.py backend\tests\test_desktop_entrypoint.py -q`

Expected: FAIL because API and worker are missing.

- [ ] **Step 3: Implement API and worker**

Include router in `router_registry.py`; start a daemon worker in desktop window mode. Worker wakes periodically, checks if today is day 1 and calls `run_scheduled_update`.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest backend\tests\test_update_center_api.py backend\tests\test_desktop_entrypoint.py -q`

Expected: PASS.

### Task 4: 前端更新中心入口

**Files:**
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/types/updateCenter.ts`
- Create: `frontend/src/components/UpdateCenterPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Test: `frontend/tests/updateCenterApi.test.mjs`
- Test: `frontend/tests/updateCenterPanel.test.mjs`

**Interfaces:**
- Produces: `fetchUpdateCenterStatus()`
- Produces: `checkUpdateCenterNow()`
- Produces: `UpdateCenterPanel`

- [ ] **Step 1: Write failing frontend tests**

Tests assert API helpers call `/api/v1/update-center/status` and `/api/v1/update-center/check`, and the dashboard exposes a “联网更新中心” panel with monthly schedule copy.

- [ ] **Step 2: Run tests to verify failure**

Run: `npm --prefix frontend test`

Expected: FAIL because helper and panel are missing.

- [ ] **Step 3: Implement minimal UI**

Add status cards for联网状态、政策包版本、下次计划检查日期、最近日志 and a “立即检查更新” button.

- [ ] **Step 4: Run tests to verify pass**

Run: `npm --prefix frontend test`

Expected: PASS.

### Task 5: 文档、打包和最终验证

**Files:**
- Modify: `README.md`
- Modify: `docs/windows-installation.md`
- Test: packaging and existing suites

- [ ] **Step 1: Document monthly update behavior**

Explain that the app checks updates on the first day of each month and can be manually checked in the update center.

- [ ] **Step 2: Run final verification**

Run:

```powershell
python -m pytest backend\tests -q
npm --prefix frontend test
npm --prefix frontend run build
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows-package.ps1 -SkipInstallerExe
git diff --check
```

Expected: all commands exit 0; Vite chunk-size warning is acceptable.
