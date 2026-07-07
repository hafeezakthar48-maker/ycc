import threading
import time
import urllib.request
import webbrowser
from collections.abc import Callable
from typing import Any

import uvicorn


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def build_uvicorn_config(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    return {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "reload": False,
        "access_log": False,
    }


def open_browser_when_ready(
    url: str,
    timeout_seconds: int = 30,
    sleep_seconds: float = 0.5,
    health_probe: Callable[[str], object] | None = None,
    browser_open: Callable[[str], object] | None = None,
) -> bool:
    probe = health_probe or _probe_health
    open_browser = browser_open or webbrowser.open
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() <= deadline:
        try:
            probe(f"{url}/health")
        except Exception:
            time.sleep(sleep_seconds)
            continue
        open_browser(url)
        return True

    return False


def run_desktop_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    url = f"http://{host}:{port}"
    opener = threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True)
    opener.start()
    uvicorn.run(**build_uvicorn_config(host=host, port=port))


def _probe_health(url: str) -> object:
    with urllib.request.urlopen(url, timeout=2) as response:
        return response.read()


if __name__ == "__main__":
    run_desktop_server()
