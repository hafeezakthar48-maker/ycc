# Windows 桌面安装包

本项目可以构建为 Windows x64 离线安装包。目标电脑不需要预装 Python、Node.js 或 npm。

## 当前发行产物

- 安装包：`output/ChinaFinanceAIAssistant-Windows-x64.zip`
- 大小：`19,593,876` 字节
- SHA256：`A32BFC7A02B1099C771C482669CC953BA5B50D3D53C889E7278E60B94450A80F`
- 内容：`ChinaFinanceAIAssistant.exe`、`install.ps1`、`launch.ps1`、`uninstall.ps1`、`README-INSTALL.txt`

说明：本机 `IExpress` 自解压安装器生成结果没有稳定内嵌主程序，构建脚本会自动跳过不可靠的 `Setup.exe`。当前可交付、可复制到其他电脑安装的发行物是 zip 安装包。

## 构建安装包

在开发电脑执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows-package.ps1
```

构建脚本会执行以下动作：

- 构建 `frontend/dist`。
- 安装后端运行依赖和 PyInstaller。
- 生成 `ChinaFinanceAIAssistant.exe`。
- 打包 `install.ps1`、`launch.ps1`、`uninstall.ps1`。
- 生成 `output/ChinaFinanceAIAssistant-Windows-x64.zip`。
- 尝试生成 IExpress 单文件安装器；如果生成结果小于主程序，会自动跳过，避免发布不可用安装器。

## 在其他电脑安装

1. 将 `output/ChinaFinanceAIAssistant-Windows-x64.zip` 复制到目标电脑。
2. 解压 zip。
3. 右键 `install.ps1`，选择“使用 PowerShell 运行”。
4. 通过桌面或开始菜单中的 `China Finance AI Assistant` 启动。

如果系统策略禁止右键运行 PowerShell，可以在解压目录打开 PowerShell 后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## 安装位置和数据目录

- 程序安装目录：`%LOCALAPPDATA%\Programs\ChinaFinanceAIAssistant`
- 用户数据目录：`%LOCALAPPDATA%\ChinaFinanceAIAssistant`
- 数据库文件：`voucher_center.sqlite3`、`formal_accounting.sqlite3`

程序安装目录可以删除或重装；用户数据目录默认保留，避免卸载时误删账务数据。

## 卸载

运行安装目录中的：

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\ChinaFinanceAIAssistant\uninstall.ps1"
```

如需同时删除本机演示数据：

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\ChinaFinanceAIAssistant\uninstall.ps1" -RemoveData
```

## 验证记录

- `python -m pytest backend/tests -q`：`279 passed, 1 warning`。
- `npm --prefix frontend test`：通过。
- `npm --prefix frontend run build`：通过，Vite 仅提示 chunk 体积超过默认阈值。
- `git diff --check`：通过。
- `powershell -NoProfile -ExecutionPolicy Bypass -File tests/packageScripts.test.ps1`：通过。
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows-package.ps1`：通过，生成 zip 安装包；Vite 仅提示 chunk 体积超过默认阈值；IExpress 安装器因体积校验未发布。
- packaged exe `/health` 检查：通过，返回 `{"status":"ok"}`。
