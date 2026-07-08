# 独立软件本体更新器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有独立桌面发行包中加入 `ChinaFinanceUpdater.exe`，让主程序可联网检查并下载软件版本升级包，由独立更新器完成校验、备份、替换和失败回滚。

**Architecture:** 主程序仍只负责本机 UI 和更新中心 API；应用升级包通过独立的 HTTPS manifest 配置发现，下载后保存到用户数据目录。实际替换文件由 `ChinaFinanceUpdater.exe` 完成，避免运行中的 `ChinaFinanceAIAssistant.exe` 自我覆盖。发行包内包含主程序、更新器和安装说明，不包含 PowerShell 安装脚本。

**Tech Stack:** FastAPI、Pydantic、Python 标准库 `zipfile` / `shutil` / `hashlib`、PyInstaller、React/Ant Design。

## Global Constraints

- 始终用简体中文文档和注释。
- 目标电脑不需要 Python、Node.js、npm 或 PowerShell 脚本依赖。
- 软件升级包只允许 HTTPS 地址，并必须通过 SHA256 校验。
- 更新器必须先备份再替换，失败时回滚已替换文件。
- 主程序不直接替换自己，只生成更新器命令或下载待安装包。
- 未配置软件更新源时，软件继续离线可用。

---

### Task 1: 应用更新清单和下载服务

**Files:**
- Modify: `backend/app/models/update_center.py`
- Modify: `backend/app/services/update_center_service.py`
- Test: `backend/tests/test_application_update_service.py`

**Interfaces:**
- Produces: `ApplicationUpdateManifest`
- Produces: `ApplicationUpdateCheckResult`
- Produces: `check_for_application_update(fetch_bytes=None, now=None) -> ApplicationUpdateCheckResult`

- [ ] **Step 1: Write failing tests**

Tests cover: HTTPS manifest is accepted, package SHA256 is verified, newer package is saved under `app-updates`, and HTTP manifests are rejected.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_application_update_service.py -q`

Expected: FAIL because application update types and function do not exist.

- [ ] **Step 3: Implement service**

Add `FINANCE_AI_APP_UPDATE_MANIFEST_URL`, parse app update manifest, compare version with `0.1.0`, download package, verify SHA256, persist package path and available version in update-center state.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest backend\tests\test_application_update_service.py -q`

Expected: PASS.

### Task 2: 独立更新器安装与回滚

**Files:**
- Create: `backend/app/updater.py`
- Test: `backend/tests/test_native_updater.py`

**Interfaces:**
- Produces: `install_update_package(package_path: Path, install_dir: Path, expected_sha256: str | None = None) -> UpdateInstallResult`
- Produces: `main(argv=None) -> int`

- [ ] **Step 1: Write failing tests**

Tests cover: valid zip replaces `ChinaFinanceAIAssistant.exe` and keeps backup; bad SHA256 refuses install; copy failure rolls back old executable.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_native_updater.py -q`

Expected: FAIL because `app.updater` does not exist.

- [ ] **Step 3: Implement updater**

Validate optional SHA256, extract zip to temp directory, back up existing files into `.update-backup`, copy files into install dir, roll back copied files on exception.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest backend\tests\test_native_updater.py -q`

Expected: PASS.

### Task 3: API 和前端软件更新入口

**Files:**
- Modify: `backend/app/api/update_center.py`
- Modify: `frontend/src/types/updateCenter.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/UpdateCenterPanel.tsx`
- Test: `backend/tests/test_update_center_api.py`
- Test: `frontend/tests/updateCenterApi.test.mjs`
- Test: `frontend/tests/updateCenterPanel.test.mjs`

**Interfaces:**
- Produces: `POST /api/v1/update-center/application/check`
- Produces: `checkApplicationUpdateNow()`

- [ ] **Step 1: Write failing tests**

Backend test checks the app update endpoint is safe when not configured. Frontend tests check helper and panel include “软件本体更新”.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_update_center_api.py -q`

Run: `npm --prefix frontend test`

Expected: FAIL because endpoint/helper/UI copy is missing.

- [ ] **Step 3: Implement API and UI**

Expose manual application update check. Display available app version, package path, and a “检查软件更新” button in update center.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest backend\tests\test_update_center_api.py -q`

Run: `npm --prefix frontend test`

Expected: PASS.

### Task 4: PyInstaller 更新器发行包

**Files:**
- Create: `backend/pyinstaller/china-finance-updater.spec`
- Modify: `scripts/build-windows-package.ps1`
- Modify: `backend/tests/test_desktop_entrypoint.py`
- Modify: `docs/windows-installation.md`
- Modify: `README.md`

**Interfaces:**
- Produces: `output/ChinaFinanceAIAssistant-Windows-x64/ChinaFinanceUpdater.exe`

- [ ] **Step 1: Write failing package tests**

Test asserts build script invokes updater spec, copies `ChinaFinanceUpdater.exe`, and docs mention native updater.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend\tests\test_desktop_entrypoint.py -q`

Expected: FAIL because updater packaging is missing.

- [ ] **Step 3: Implement packaging**

Add updater PyInstaller spec, build both specs, copy both exes to stage, update README-INSTALL text and docs. Keep IExpress launch target as `ChinaFinanceAIAssistant.exe`.

- [ ] **Step 4: Run final verification**

Run:

```powershell
python -m pytest backend\tests -q
npm --prefix frontend test
npm --prefix frontend run build
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows-package.ps1 -SkipInstallerExe
git diff --check
```

Expected: all commands exit 0; Vite chunk-size warning is acceptable.
