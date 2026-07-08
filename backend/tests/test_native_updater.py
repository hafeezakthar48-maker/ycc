import hashlib
import zipfile
from pathlib import Path

import pytest

from app.updater import install_update_package, main


def _write_package(path: Path, files: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_install_update_package_replaces_application_and_keeps_backup(tmp_path):
    install_dir = tmp_path / "app"
    install_dir.mkdir()
    target = install_dir / "ChinaFinanceAIAssistant.exe"
    target.write_bytes(b"old exe")
    package = tmp_path / "update.zip"
    digest = _write_package(package, {"ChinaFinanceAIAssistant.exe": b"new exe", "README-INSTALL.txt": b"readme"})

    result = install_update_package(package, install_dir, expected_sha256=digest)

    assert result.installed is True
    assert target.read_bytes() == b"new exe"
    assert (install_dir / ".update-backup" / "ChinaFinanceAIAssistant.exe").read_bytes() == b"old exe"
    assert result.installed_files == ["ChinaFinanceAIAssistant.exe", "README-INSTALL.txt"]


def test_install_update_package_rejects_sha256_mismatch(tmp_path):
    install_dir = tmp_path / "app"
    install_dir.mkdir()
    target = install_dir / "ChinaFinanceAIAssistant.exe"
    target.write_bytes(b"old exe")
    package = tmp_path / "update.zip"
    _write_package(package, {"ChinaFinanceAIAssistant.exe": b"new exe"})

    with pytest.raises(ValueError, match="SHA256"):
        install_update_package(package, install_dir, expected_sha256="0" * 64)

    assert target.read_bytes() == b"old exe"


def test_install_update_package_rolls_back_when_copy_fails(tmp_path):
    install_dir = tmp_path / "app"
    install_dir.mkdir()
    target = install_dir / "ChinaFinanceAIAssistant.exe"
    target.write_bytes(b"old exe")
    package = tmp_path / "update.zip"
    digest = _write_package(package, {"ChinaFinanceAIAssistant.exe": b"new exe", "../evil.txt": b"blocked"})

    with pytest.raises(ValueError, match="不允许"):
        install_update_package(package, install_dir, expected_sha256=digest)

    assert target.read_bytes() == b"old exe"
    assert not (tmp_path / "evil.txt").exists()


def test_updater_main_installs_package_from_cli(tmp_path):
    install_dir = tmp_path / "app"
    install_dir.mkdir()
    (install_dir / "ChinaFinanceAIAssistant.exe").write_bytes(b"old exe")
    package = tmp_path / "update.zip"
    digest = _write_package(package, {"ChinaFinanceAIAssistant.exe": b"new exe"})

    exit_code = main(["--package", str(package), "--install-dir", str(install_dir), "--sha256", digest])

    assert exit_code == 0
    assert (install_dir / "ChinaFinanceAIAssistant.exe").read_bytes() == b"new exe"
