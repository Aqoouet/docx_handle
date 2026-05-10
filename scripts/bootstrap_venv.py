from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _seed_pywin32_dlls(venv_dir: Path) -> None:
    if os.name != "nt":
        return

    base_root = Path(sys.executable).resolve().parent
    system32_dir = base_root / "Lib" / "site-packages" / "pywin32_system32"
    if not system32_dir.exists():
        return

    scripts_dir = venv_dir / "Scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    site_packages = venv_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    venv_system32_dir = site_packages / "pywin32_system32"
    venv_system32_dir.mkdir(parents=True, exist_ok=True)

    for dll_name in ("pywintypes310.dll", "pythoncom310.dll"):
        source = system32_dir / dll_name
        if source.exists():
            shutil.copy2(source, scripts_dir / dll_name)
            shutil.copy2(source, venv_system32_dir / dll_name)

    pth_file = site_packages / "pywin32_system32.pth"
    pth_file.write_text(f"{venv_system32_dir}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and seed a local virtual environment.")
    parser.add_argument("--venv-dir", default=".venv", help="Virtual environment directory.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete the existing virtual environment before creating it again.",
    )
    parser.add_argument(
        "--no-system-site-packages",
        action="store_false",
        dest="system_site_packages",
        help="Create an isolated venv without base interpreter packages.",
    )
    parser.add_argument(
        "--install-requirements",
        action="store_true",
        help="Install requirements after creating the venv.",
    )
    parser.add_argument("--requirements", default="requirements.txt", help="Requirements file.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = (repo_root / args.venv_dir).resolve()
    requirements = (repo_root / args.requirements).resolve()

    builder = venv.EnvBuilder(with_pip=True, system_site_packages=args.system_site_packages)
    if args.recreate and venv_dir.exists():
        shutil.rmtree(venv_dir)

    if not venv_dir.exists():
        builder.create(venv_dir)
    _seed_pywin32_dlls(venv_dir)

    python_exe = _venv_python(venv_dir)
    if args.install_requirements:
        subprocess.run([str(python_exe), "-m", "pip", "install", "-r", str(requirements)], check=True)
    print(f"Virtual environment ready: {venv_dir}")
    print(f"Run: {python_exe} -m docx_handle.cli --host 0.0.0.0 --port 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
