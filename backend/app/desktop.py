import threading
import time
import urllib.request
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Any

import uvicorn

from app.runtime_paths import get_user_data_dir
from app.services.update_center_service import run_scheduled_update


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_WINDOW_TITLE = "中国财务 AI 助手"
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 920
DEFAULT_WINDOW_MIN_SIZE = (1180, 760)
DEFAULT_UPDATE_CHECK_INTERVAL_SECONDS = 60 * 60


def build_uvicorn_config(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    return {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "reload": False,
        "access_log": False,
        "log_config": None,
    }


def open_desktop_window(
    url: str,
    create_window: Callable[..., object] | None = None,
    start: Callable[..., object] | None = None,
) -> None:
    if create_window is None or start is None:
        import webview

        create_window = create_window or webview.create_window
        start = start or webview.start

    create_window(
        DEFAULT_WINDOW_TITLE,
        url,
        width=DEFAULT_WINDOW_WIDTH,
        height=DEFAULT_WINDOW_HEIGHT,
        min_size=DEFAULT_WINDOW_MIN_SIZE,
        background_color="#f5f7fb",
        confirm_close=True,
        text_select=True,
    )
    start()


def open_desktop_window_when_ready(
    url: str,
    timeout_seconds: int = 30,
    sleep_seconds: float = 0.5,
    health_probe: Callable[[str], object] | None = None,
    window_open: Callable[[str], object] | None = None,
) -> bool:
    probe = health_probe or _probe_health
    open_window = window_open or open_desktop_window
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() <= deadline:
        try:
            probe(f"{url}/health")
        except Exception:
            time.sleep(sleep_seconds)
            continue
        open_window(url)
        return True

    return False


def run_backend_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        _write_desktop_log(f"启动内置后端：{host}:{port}")
        config = uvicorn.Config(**build_uvicorn_config(host=host, port=port))
        server = uvicorn.Server(config)
        server.install_signal_handlers = lambda: None
        server.run()
    except Exception:
        _write_desktop_log(f"内置后端启动失败：\n{traceback.format_exc()}")
        raise


def run_desktop_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    window_opener: Callable[[str], bool] | None = None,
    backend_runner: Callable[..., object] | None = None,
    update_worker_starter: Callable[[], object] | None = None,
) -> None:
    url = f"http://{host}:{port}"
    runner = backend_runner or run_backend_server

    def backend_target(**kwargs: object) -> None:
        try:
            runner(**kwargs)
        except Exception:
            _write_desktop_log(f"后台线程异常：\n{traceback.format_exc()}")
            raise

    server = threading.Thread(
        target=backend_target,
        kwargs={"host": host, "port": port},
        daemon=True,
    )
    server.start()
    start_updates = update_worker_starter or start_monthly_update_worker
    start_updates()
    opener = window_opener or open_desktop_window_when_ready
    if not opener(url):
        _write_desktop_log("桌面窗口启动失败：后端服务未在限定时间内就绪。")
        raise RuntimeError("桌面窗口启动失败：后端服务未在限定时间内就绪。")


def _probe_health(url: str) -> object:
    with urllib.request.urlopen(url, timeout=2) as response:
        return response.read()


def start_monthly_update_worker(interval_seconds: int = DEFAULT_UPDATE_CHECK_INTERVAL_SECONDS) -> threading.Thread:
    worker = threading.Thread(
        target=_monthly_update_worker_loop,
        kwargs={"interval_seconds": interval_seconds},
        daemon=True,
    )
    worker.start()
    return worker


def _monthly_update_worker_loop(interval_seconds: int = DEFAULT_UPDATE_CHECK_INTERVAL_SECONDS) -> None:
    while True:
        try:
            run_scheduled_update(now=datetime.now())
        except Exception:
            _write_desktop_log(f"月度联网更新检查失败：\n{traceback.format_exc()}")
        time.sleep(interval_seconds)


def _write_desktop_log(message: str) -> None:
    try:
        log_dir = get_user_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")
        with (log_dir / "desktop.log").open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception:
        return


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    _write_desktop_log(f"桌面入口启动，参数：{args}")
    if "--server-only" in args:
        run_backend_server()
        return
    run_desktop_server()


if __name__ == "__main__":
    main()
