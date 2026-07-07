# Windows 桌面安装包

本项目可以构建为 Windows x64 离线安装包。目标电脑不需要预装 Python、Node.js 或 npm。

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
- 如果系统存在 `iexpress.exe`，额外尝试生成 `output/ChinaFinanceAIAssistant-Windows-x64-Setup.exe`。

## 在其他电脑安装

推荐方式：

1. 将 `output/ChinaFinanceAIAssistant-Windows-x64.zip` 复制到目标电脑。
2. 解压 zip。
3. 右键 `install.ps1`，选择“使用 PowerShell 运行”。
4. 通过桌面或开始菜单中的 `China Finance AI Assistant` 启动。

如果生成了 `ChinaFinanceAIAssistant-Windows-x64-Setup.exe`，也可以直接复制并运行该安装器。

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
