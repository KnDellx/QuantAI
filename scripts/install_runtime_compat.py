"""Install the project-local Python startup hook into the active virtualenv."""

from __future__ import annotations

import sysconfig
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PTH_FILENAME = "quantai_runtime_compat.pth"


def install_runtime_hook(site_packages: Path | None = None) -> Path:
    """Make the repository's sitecustomize module load in the active environment."""

    target_dir = site_packages or Path(sysconfig.get_path("purelib"))
    target = target_dir / PTH_FILENAME
    target.write_text(f"{PROJECT_ROOT}\nimport sitecustomize\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    installed_path = install_runtime_hook()
    print(f"Installed runtime compatibility hook: {installed_path}")
