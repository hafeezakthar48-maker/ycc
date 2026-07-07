# Windows 桌面安装包实施计划

> **给自动化执行代理：** 必须使用 `superpowers:executing-plans` 按任务逐项执行。本计划使用 checkbox（`- [ ]`）跟踪进度。

**目标：** 将现有前后端开发态项目打包为可复制到其他 Windows 电脑安装运行的离线桌面发行包。

**架构：** 后端 FastAPI 在发行模式下同时托管前端 `dist` 静态文件，并通过 PyInstaller 打成单个本地服务 `exe`。发行包使用 PowerShell 安装脚本复制到用户目录、创建桌面和开始菜单快捷方式，并生成 zip；如果本机具备 `IExpress`，额外生成单文件自解压安装器。

**技术栈：** FastAPI、Uvicorn、React/Vite、PyInstaller、PowerShell、IExpress。

## 全局约束

- 所有说明、文档和新增代码注释使用简体中文。
- 不要求目标电脑安装 Python、Node.js 或 npm。
- 运行数据必须写入用户可写目录，不能依赖安装目录可写。
- 安装包优先支持 Windows x64；跨平台安装器后续单独规划。
- 保留现有开发启动方式和测试命令。

---

### Task 1: 发行模式静态托管与可写数据目录

**文件：**
- 新建：`backend/app/runtime_paths.py`
- 修改：`backend/app/main.py`
- 修改：`backend/app/services/accounting_service.py`
- 修改：`backend/app/services/voucher_center_service.py`
- 新建：`backend/tests/test_desktop_runtime.py`

**接口：**
- 产出：`get_user_data_dir() -> Path`
- 产出：`get_default_database_path(filename: str) -> Path`
- 产出：`get_frontend_dist_dir() -> Path | None`
- 消费：`FINANCE_AI_DATA_DIR`、`FINANCE_AI_FRONTEND_DIST`

- [ ] **Step 1: 写失败测试**

```python
def test_default_database_path_uses_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path / "finance-data"))
    from app.runtime_paths import get_default_database_path

    assert get_default_database_path("voucher_center.sqlite3") == tmp_path / "finance-data" / "voucher_center.sqlite3"
```

- [ ] **Step 2: 运行测试确认失败**

运行：`python -m pytest backend/tests/test_desktop_runtime.py -q`

预期：失败，原因是 `app.runtime_paths` 尚不存在。

- [ ] **Step 3: 最小实现**

新增 `backend/app/runtime_paths.py`，并改造两个 SQLite 默认路径；`backend/app/main.py` 在存在前端构建目录时挂载 `/assets`、根路径和 SPA fallback。

- [ ] **Step 4: 运行测试确认通过**

运行：`python -m pytest backend/tests/test_desktop_runtime.py backend/tests/test_voucher_center_persistence.py backend/tests/test_accounting_period_service.py -q`

预期：全部通过。

- [ ] **Step 5: 提交**

```powershell
git add backend/app/runtime_paths.py backend/app/main.py backend/app/services/accounting_service.py backend/app/services/voucher_center_service.py backend/tests/test_desktop_runtime.py
git commit -m "feat: prepare backend for desktop runtime"
```

### Task 2: 桌面启动入口与 PyInstaller 配置

**文件：**
- 新建：`backend/app/desktop.py`
- 新建：`backend/pyinstaller/china-finance-ai-assistant.spec`
- 新建：`backend/tests/test_desktop_entrypoint.py`

**接口：**
- 产出：`build_uvicorn_config(host: str = "127.0.0.1", port: int = 8000) -> dict[str, object]`
- 产出：`open_browser_when_ready(url: str, timeout_seconds: int = 30) -> bool`

- [ ] **Step 1: 写失败测试**

```python
def test_desktop_entrypoint_builds_local_uvicorn_config():
    from app.desktop import build_uvicorn_config

    config = build_uvicorn_config()

    assert config["app"] == "app.main:app"
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 8000
```

- [ ] **Step 2: 运行测试确认失败**

运行：`python -m pytest backend/tests/test_desktop_entrypoint.py -q`

预期：失败，原因是 `app.desktop` 尚不存在。

- [ ] **Step 3: 最小实现**

新增桌面入口，启动本机服务并自动打开浏览器；新增 PyInstaller spec，将 `frontend/dist` 打包为 `frontend_dist` 数据目录。

- [ ] **Step 4: 运行测试确认通过**

运行：`python -m pytest backend/tests/test_desktop_entrypoint.py -q`

预期：通过。

- [ ] **Step 5: 提交**

```powershell
git add backend/app/desktop.py backend/pyinstaller/china-finance-ai-assistant.spec backend/tests/test_desktop_entrypoint.py
git commit -m "feat: add desktop backend executable entrypoint"
```

### Task 3: Windows 发行包构建与安装脚本

**文件：**
- 新建：`scripts/build-windows-package.ps1`
- 新建：`scripts/installer/install.ps1`
- 新建：`scripts/installer/uninstall.ps1`
- 新建：`scripts/installer/launch.ps1`
- 新建：`docs/windows-installation.md`
- 新建：`tests/packageScripts.test.ps1`

**接口：**
- 产出：`output/ChinaFinanceAIAssistant-Windows-x64.zip`
- 可选产出：`output/ChinaFinanceAIAssistant-Windows-x64-Setup.exe`

- [ ] **Step 1: 写失败测试**

```powershell
Describe "Windows package scripts" {
  It "contains installer and uninstall scripts" {
    Test-Path "scripts/installer/install.ps1" | Should -BeTrue
    Test-Path "scripts/installer/uninstall.ps1" | Should -BeTrue
  }
}
```

- [ ] **Step 2: 运行测试确认失败**

运行：`pwsh -NoProfile -ExecutionPolicy Bypass -File tests/packageScripts.test.ps1`

预期：失败，原因是脚本文件尚不存在。

- [ ] **Step 3: 最小实现**

新增构建脚本：安装前端依赖、构建前端、安装 PyInstaller、生成后端 exe、复制安装脚本、打 zip、尝试生成 IExpress 单文件安装器。

- [ ] **Step 4: 构建并验证**

运行：`powershell -ExecutionPolicy Bypass -File scripts/build-windows-package.ps1`

预期：生成 zip；如果 `iexpress.exe` 可用，同时生成 setup exe。

- [ ] **Step 5: 提交**

```powershell
git add scripts/build-windows-package.ps1 scripts/installer/install.ps1 scripts/installer/uninstall.ps1 scripts/installer/launch.ps1 docs/windows-installation.md tests/packageScripts.test.ps1
git commit -m "feat: add windows installer packaging"
```

### Task 4: 全量验证与发行记录

**文件：**
- 修改：`README.md`
- 修改：`docs/windows-installation.md`

**接口：**
- 消费：Task 3 生成的发行产物路径。
- 产出：README 中的安装包使用说明和验证记录。

- [ ] **Step 1: 运行全量验证**

```powershell
python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

- [ ] **Step 2: 运行安装包构建**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows-package.ps1
```

- [ ] **Step 3: 记录产物**

把 zip 和可选 setup exe 路径写入 `docs/windows-installation.md` 与 `README.md`。

- [ ] **Step 4: 提交**

```powershell
git add README.md docs/windows-installation.md
git commit -m "docs: document windows desktop package"
```
