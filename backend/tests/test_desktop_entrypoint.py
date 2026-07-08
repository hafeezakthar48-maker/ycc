from pathlib import Path
from unittest.mock import Mock


def test_desktop_entrypoint_builds_local_uvicorn_config():
    from app.desktop import build_uvicorn_config

    config = build_uvicorn_config()

    assert config["app"] == "app.main:app"
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 8000
    assert config["reload"] is False
    assert config["access_log"] is False
    assert config["log_config"] is None


def test_open_desktop_window_when_ready_returns_true_after_health_check():
    from app.desktop import open_desktop_window_when_ready

    window_opener = Mock()
    responses = iter([Exception("not ready"), object()])

    def health_probe(_url: str):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    result = open_desktop_window_when_ready(
        "http://127.0.0.1:8000",
        timeout_seconds=1,
        sleep_seconds=0,
        health_probe=health_probe,
        window_open=window_opener,
    )

    assert result is True
    window_opener.assert_called_once_with("http://127.0.0.1:8000")


def test_open_desktop_window_when_ready_returns_false_after_timeout():
    from app.desktop import open_desktop_window_when_ready

    window_opener = Mock()

    result = open_desktop_window_when_ready(
        "http://127.0.0.1:8000",
        timeout_seconds=0,
        sleep_seconds=0,
        health_probe=Mock(side_effect=Exception("not ready")),
        window_open=window_opener,
    )

    assert result is False
    window_opener.assert_not_called()


def test_open_desktop_window_uses_native_window_configuration():
    from app.desktop import (
        DEFAULT_WINDOW_HEIGHT,
        DEFAULT_WINDOW_MIN_SIZE,
        DEFAULT_WINDOW_TITLE,
        DEFAULT_WINDOW_WIDTH,
        open_desktop_window,
    )

    create_window = Mock()
    start = Mock()

    open_desktop_window(
        "http://127.0.0.1:8000",
        create_window=create_window,
        start=start,
    )

    create_window.assert_called_once_with(
        DEFAULT_WINDOW_TITLE,
        "http://127.0.0.1:8000",
        width=DEFAULT_WINDOW_WIDTH,
        height=DEFAULT_WINDOW_HEIGHT,
        min_size=DEFAULT_WINDOW_MIN_SIZE,
        background_color="#f5f7fb",
        confirm_close=True,
        text_select=True,
    )
    start.assert_called_once()


def test_run_desktop_server_starts_backend_before_window(monkeypatch):
    import app.desktop as desktop

    calls: list[str] = []

    class ImmediateThread:
        def __init__(self, target, kwargs, daemon):
            self.target = target
            self.kwargs = kwargs
            self.daemon = daemon

        def start(self):
            calls.append("thread.start")
            self.target(**self.kwargs)

    backend_runner = Mock(side_effect=lambda **_kwargs: calls.append("backend.run"))
    window_opener = Mock(side_effect=lambda _url: calls.append("window.open") or True)
    update_worker_starter = Mock(side_effect=lambda: calls.append("updates.start"))

    monkeypatch.setattr(desktop.threading, "Thread", ImmediateThread)

    desktop.run_desktop_server(
        window_opener=window_opener,
        backend_runner=backend_runner,
        update_worker_starter=update_worker_starter,
    )

    assert calls == ["thread.start", "backend.run", "updates.start", "window.open"]
    backend_runner.assert_called_once_with(host="127.0.0.1", port=8000)
    update_worker_starter.assert_called_once_with()
    window_opener.assert_called_once_with("http://127.0.0.1:8000")


def test_start_monthly_update_worker_creates_daemon_thread(monkeypatch):
    import app.desktop as desktop

    created: dict[str, object] = {}

    class FakeThread:
        def __init__(self, target, kwargs, daemon):
            created["target"] = target
            created["kwargs"] = kwargs
            created["daemon"] = daemon
            self.started = False

        def start(self):
            self.started = True
            created["started"] = True

    monkeypatch.setattr(desktop.threading, "Thread", FakeThread)

    thread = desktop.start_monthly_update_worker(interval_seconds=300)

    assert thread.started is True
    assert created["daemon"] is True
    assert created["kwargs"]["interval_seconds"] == 300


def test_desktop_main_server_only_does_not_start_monthly_update_worker(monkeypatch):
    import app.desktop as desktop

    backend_runner = Mock()
    desktop_runner = Mock()
    update_worker_starter = Mock()

    monkeypatch.setattr(desktop, "run_backend_server", backend_runner)
    monkeypatch.setattr(desktop, "run_desktop_server", desktop_runner)
    monkeypatch.setattr(desktop, "start_monthly_update_worker", update_worker_starter)

    desktop.main(["--server-only"])

    backend_runner.assert_called_once_with()
    desktop_runner.assert_not_called()
    update_worker_starter.assert_not_called()


def test_run_backend_server_disables_uvicorn_signal_handlers(monkeypatch):
    import app.desktop as desktop

    calls: list[str] = []

    class FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeServer:
        def __init__(self, config):
            self.config = config
            self.install_signal_handlers = self._install_signal_handlers

        def _install_signal_handlers(self):
            calls.append("signals")

        def run(self):
            self.install_signal_handlers()
            calls.append("run")

    monkeypatch.setattr(desktop.uvicorn, "Config", FakeConfig)
    monkeypatch.setattr(desktop.uvicorn, "Server", FakeServer)

    desktop.run_backend_server()

    assert calls == ["run"]


def test_desktop_main_supports_server_only_mode(monkeypatch):
    import app.desktop as desktop

    backend_runner = Mock()
    desktop_runner = Mock()

    monkeypatch.setattr(desktop, "run_backend_server", backend_runner)
    monkeypatch.setattr(desktop, "run_desktop_server", desktop_runner)

    desktop.main(["--server-only"])

    backend_runner.assert_called_once_with()
    desktop_runner.assert_not_called()


def test_desktop_main_opens_native_window_by_default(monkeypatch):
    import app.desktop as desktop

    backend_runner = Mock()
    desktop_runner = Mock()

    monkeypatch.setattr(desktop, "run_backend_server", backend_runner)
    monkeypatch.setattr(desktop, "run_desktop_server", desktop_runner)

    desktop.main([])

    desktop_runner.assert_called_once_with()
    backend_runner.assert_not_called()


def test_pyinstaller_spec_points_to_backend_desktop_entrypoint():
    spec_path = Path(__file__).resolve().parents[1] / "pyinstaller" / "china-finance-ai-assistant.spec"
    content = spec_path.read_text(encoding="utf-8")

    assert 'backend_root = Path(SPECPATH).resolve().parent' in content
    assert 'backend_root / "app" / "desktop.py"' in content
    assert 'collect_submodules("app")' in content
    assert 'collect_submodules("webview")' in content


def test_pyinstaller_spec_embeds_windows_icon():
    spec_path = Path(__file__).resolve().parents[1] / "pyinstaller" / "china-finance-ai-assistant.spec"
    content = spec_path.read_text(encoding="utf-8")

    assert 'assets_root = backend_root / "assets"' in content
    assert 'icon=str(assets_root / "app-icon.ico")' in content
    assert "console=False" in content


def test_pyinstaller_updater_spec_points_to_native_updater_entrypoint():
    spec_path = Path(__file__).resolve().parents[1] / "pyinstaller" / "china-finance-updater.spec"

    assert spec_path.exists()
    content = spec_path.read_text(encoding="utf-8")
    assert 'backend_root / "app" / "updater.py"' in content
    assert 'name="ChinaFinanceUpdater"' in content
    assert "console=False" in content


def test_windows_package_is_portable_exe_without_powershell_installer():
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "build-windows-package.ps1"
    docs_path = root / "docs" / "windows-installation.md"
    readme_path = root / "README.md"

    script = script_path.read_text(encoding="utf-8")
    docs = docs_path.read_text(encoding="utf-8")
    readme = readme_path.read_text(encoding="utf-8")

    assert "powershell.exe" not in script
    assert "install.ps1" not in script
    assert "Copy-Item -Path (Join-Path $PSScriptRoot \"installer\\*.ps1\")" not in script
    assert "双击 `ChinaFinanceAIAssistant.exe`" in docs
    assert "ChinaFinanceUpdater.exe" in script
    assert "ChinaFinanceUpdater.exe" in docs
    assert "ChinaFinanceUpdater.exe" in readme
    assert "目标电脑无需安装 Python、Node.js、npm 或 PowerShell 脚本依赖" in readme
