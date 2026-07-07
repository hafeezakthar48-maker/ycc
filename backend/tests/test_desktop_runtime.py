from pathlib import Path


def test_default_database_path_uses_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCE_AI_DATA_DIR", str(tmp_path / "finance-data"))

    from app.runtime_paths import get_default_database_path

    assert get_default_database_path("voucher_center.sqlite3") == tmp_path / "finance-data" / "voucher_center.sqlite3"


def test_frontend_dist_dir_prefers_environment_override(monkeypatch, tmp_path):
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    monkeypatch.setenv("FINANCE_AI_FRONTEND_DIST", str(frontend_dist))

    from app.runtime_paths import get_frontend_dist_dir

    assert get_frontend_dist_dir() == frontend_dist


def test_frontend_dist_dir_ignores_missing_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCE_AI_FRONTEND_DIST", str(tmp_path / "missing-dist"))

    from app.runtime_paths import get_frontend_dist_dir

    assert get_frontend_dist_dir() is None
