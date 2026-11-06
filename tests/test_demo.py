"""Checks the demo site in demo/ still starts, so it can't break unnoticed.

The demo runs in a separate process because it has its own settings.
"""

import os
import subprocess  # noqa: S404
import sys
from pathlib import Path

MANAGE = Path(__file__).resolve().parent.parent / "demo" / "manage.py"


def run_manage(*args):
    # Drop the test settings pytest set, so the demo uses its own.
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    return subprocess.run(  # noqa: S603
        [sys.executable, str(MANAGE), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_site_passes_django_checks():
    result = run_manage("check")
    assert result.returncode == 0, result.stderr
