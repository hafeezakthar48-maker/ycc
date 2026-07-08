import argparse
import hashlib
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateInstallResult:
    installed: bool
    installed_files: list[str]
    backup_dir: Path


def install_update_package(
    package_path: Path,
    install_dir: Path,
    expected_sha256: str | None = None,
) -> UpdateInstallResult:
    package_path = package_path.resolve()
    install_dir = install_dir.resolve()
    if expected_sha256:
        actual_sha256 = hashlib.sha256(package_path.read_bytes()).hexdigest()
        if actual_sha256.lower() != expected_sha256.lower():
            raise ValueError(f"更新包 SHA256 校验失败：期望 {expected_sha256}，实际 {actual_sha256}")

    if not zipfile.is_zipfile(package_path):
        raise ValueError("更新包不是有效的 zip 文件")

    install_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = install_dir / ".update-backup"
    copied_files: list[Path] = []

    with zipfile.ZipFile(package_path) as archive:
        file_names = [name for name in archive.namelist() if not name.endswith("/")]
        _validate_archive_paths(file_names)

        with tempfile.TemporaryDirectory(prefix=".update-staging-", dir=install_dir) as staging_name:
            staging_dir = Path(staging_name)
            archive.extractall(staging_dir)

            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            try:
                for relative_name in file_names:
                    source = staging_dir / relative_name
                    target = install_dir / relative_name
                    target.parent.mkdir(parents=True, exist_ok=True)

                    if target.exists():
                        backup_target = backup_dir / relative_name
                        backup_target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup_target)

                    shutil.copy2(source, target)
                    copied_files.append(target)
            except Exception:
                _rollback(copied_files, backup_dir, install_dir)
                raise

    return UpdateInstallResult(installed=True, installed_files=file_names, backup_dir=backup_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="中国财务 AI 助手独立更新器")
    parser.add_argument("--package", required=True, help="已下载的软件更新 zip 包")
    parser.add_argument("--install-dir", required=True, help="需要替换的安装目录")
    parser.add_argument("--sha256", default=None, help="可选的更新包 SHA256")
    args = parser.parse_args(argv)

    install_update_package(Path(args.package), Path(args.install_dir), expected_sha256=args.sha256)
    return 0


def _validate_archive_paths(file_names: list[str]) -> None:
    for name in file_names:
        normalized = Path(name)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"更新包内路径不允许写出安装目录：{name}")


def _rollback(copied_files: list[Path], backup_dir: Path, install_dir: Path) -> None:
    for target in reversed(copied_files):
        relative_name = target.relative_to(install_dir)
        backup_source = backup_dir / relative_name
        if backup_source.exists():
            shutil.copy2(backup_source, target)
        elif target.exists():
            target.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
