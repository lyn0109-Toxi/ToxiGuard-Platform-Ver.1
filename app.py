from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
VENDOR = ROOT / "vendor_py314"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

import toxiguard_platform.app  # noqa: F401,E402
