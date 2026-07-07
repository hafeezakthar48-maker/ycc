from unittest.mock import Mock


def test_desktop_entrypoint_builds_local_uvicorn_config():
    from app.desktop import build_uvicorn_config

    config = build_uvicorn_config()

    assert config["app"] == "app.main:app"
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 8000
    assert config["reload"] is False
    assert config["access_log"] is False


def test_open_browser_when_ready_returns_true_after_health_check():
    from app.desktop import open_browser_when_ready

    opener = Mock()
    responses = iter([Exception("not ready"), object()])

    def health_probe(_url: str):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    result = open_browser_when_ready(
        "http://127.0.0.1:8000",
        timeout_seconds=1,
        sleep_seconds=0,
        health_probe=health_probe,
        browser_open=opener,
    )

    assert result is True
    opener.assert_called_once_with("http://127.0.0.1:8000")


def test_open_browser_when_ready_returns_false_after_timeout():
    from app.desktop import open_browser_when_ready

    opener = Mock()

    result = open_browser_when_ready(
        "http://127.0.0.1:8000",
        timeout_seconds=0,
        sleep_seconds=0,
        health_probe=Mock(side_effect=Exception("not ready")),
        browser_open=opener,
    )

    assert result is False
    opener.assert_not_called()
