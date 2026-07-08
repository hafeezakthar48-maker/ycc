# Windows 桌面发行包

本项目可以构建为 Windows x64 独立桌面应用。目标电脑不需要预装 Python、Node.js、npm，也不需要运行 PowerShell 安装脚本。

## 当前发行产物

- 便携发行包：`output/ChinaFinanceAIAssistant-Windows-x64.zip`
- 主程序：`ChinaFinanceAIAssistant.exe`
- 包内容：`ChinaFinanceAIAssistant.exe`、`ChinaFinanceUpdater.exe`、`README-INSTALL.txt`

说明：zip 解压后就是可运行目录。主程序会在本机启动内置后端服务，并打开独立桌面窗口，不显示浏览器地址栏。

## 联网更新中心

桌面版已内置联网更新中心。软件启动后仍然本地运行，前端只访问本机 `127.0.0.1:8000`，由内置后端负责访问企业配置的 HTTPS 更新源。

默认规则：

- 每月 1 号自动检查一次法规、税率与政策数据包。
- 当天已经记录过自动检查后，不会重复刷屏。
- 支持在“企业设置 > 联网更新中心”手动检查更新。
- 仅允许 HTTPS 更新清单和 HTTPS 政策包地址。
- 下载后先做 SHA256 校验，校验失败不会替换本地政策包。
- 未配置更新清单时，软件继续离线使用，并在更新中心显示“未配置”状态。
- 更新包安装后会参与本地法规库检索；正式财税判断仍需财务或税务负责人复核。

## 软件本体更新器

发行包内包含 `ChinaFinanceUpdater.exe`。这是原生独立更新器，用于安装软件本体升级包，不是 PowerShell 脚本，也不需要目标电脑安装 Python 或 Node.js。

工作方式：

- 主程序在“联网更新中心”检查软件本体更新。
- 发现新版本后，主程序下载 HTTPS 软件升级 zip 包并校验 SHA256。
- 更新包保存到 `%LOCALAPPDATA%\ChinaFinanceAIAssistant\app-updates`。
- 安装软件本体更新时，由 `ChinaFinanceUpdater.exe` 先备份当前安装目录文件，再替换新版本文件。
- 更新失败会恢复已备份文件。

软件本体更新清单环境变量：

```powershell
$env:FINANCE_AI_APP_UPDATE_MANIFEST_URL="https://your-company.example.com/china-finance-ai/app/manifest.json"
```

软件本体更新清单格式：

```json
{
  "version": "0.2.0",
  "published_at": "2026-08-01T00:00:00+08:00",
  "package_url": "https://your-company.example.com/china-finance-ai/app/ChinaFinanceAIAssistant-0.2.0.zip",
  "sha256": "64位小写或大写SHA256",
  "summary": "软件本体 0.2.0 更新包",
  "mandatory": false
}
```

可选企业配置：

```powershell
$env:FINANCE_AI_UPDATE_MANIFEST_URL="https://your-company.example.com/china-finance-ai/policy/manifest.json"
$env:FINANCE_AI_UPDATE_CHANNEL="stable"
$env:FINANCE_AI_UPDATE_PROXY="https://proxy.example.com:8080"
```

这些环境变量只用于启动后的联网更新配置，不是运行依赖。企业内网也可以通过统一终端管理工具下发同名环境变量。

更新清单格式：

```json
{
  "version": "2026.08",
  "published_at": "2026-08-01T00:00:00+08:00",
  "package_url": "https://your-company.example.com/china-finance-ai/policy/policy-2026-08.json",
  "sha256": "64位小写或大写SHA256",
  "summary": "2026年8月法规、税率与政策数据包"
}
```

政策包格式：

```json
{
  "documents": [
    {
      "id": "policy-2026-08-example",
      "title": "政策标题",
      "authority": "发布机关",
      "document_number": "文号",
      "category": "税收法规",
      "published_date": "2026-08-01",
      "effective_date": "2026-08-01",
      "status": "需复核",
      "source_url": "https://example.com/policy.html",
      "updated_at": "2026-08-01",
      "keywords": ["关键词"],
      "summary": "摘要",
      "content": "正文或可检索片段"
    }
  ]
}
```

## 构建发行包

在开发电脑执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows-package.ps1
```

构建脚本会执行以下动作：

- 构建 `frontend/dist`。
- 安装后端运行依赖和 PyInstaller。
- 生成独立窗口主程序 `ChinaFinanceAIAssistant.exe`。
- 生成 `output/ChinaFinanceAIAssistant-Windows-x64.zip`。
- 可选生成 IExpress 自解压启动文件；自解压文件直接启动主程序，不调用 PowerShell。

## 在其他电脑运行

1. 将 `output/ChinaFinanceAIAssistant-Windows-x64.zip` 复制到目标电脑。
2. 解压 zip 到任意目录。
3. 双击 `ChinaFinanceAIAssistant.exe`。

需要桌面快捷方式时，右键 `ChinaFinanceAIAssistant.exe`，选择“发送到 > 桌面快捷方式”。

## 数据目录

- 用户数据目录：`%LOCALAPPDATA%\ChinaFinanceAIAssistant`
- 数据库文件：`voucher_center.sqlite3`、`formal_accounting.sqlite3`
- 更新中心状态：`update-center.json`
- 联网政策包目录：`policy-packages`
- 软件本体更新包目录：`app-updates`

程序目录可以删除或替换；用户数据目录默认保留，避免误删账务演示数据和已安装政策包。

## 卸载

1. 关闭 `ChinaFinanceAIAssistant.exe`。
2. 删除解压出来的程序目录。
3. 如需同时删除演示数据和政策包，再手动删除 `%LOCALAPPDATA%\ChinaFinanceAIAssistant`。

## 验证记录

- `python -m pytest backend/tests -q`：通过。
- `npm --prefix frontend test`：通过。
- `npm --prefix frontend run build`：通过；Vite 仅提示 chunk 体积超过默认阈值。
- `git diff --check`：通过。
- `scripts/build-windows-package.ps1`：生成 zip 发行包；发行包内主程序可直接双击运行。
