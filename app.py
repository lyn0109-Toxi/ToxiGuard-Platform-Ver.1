from __future__ import annotations

import platform
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
VENDOR = ROOT / "vendor_py314"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

try:
    import toxiguard_platform.app  # noqa: F401,E402
except Exception as exc:  # pragma: no cover - deployment diagnostic guard
    import streamlit as st

    st.error("ToxiGuard-Platform Ver.1 could not finish startup.")
    st.write(
        "The app entry point loaded, but the main application raised an exception "
        "before the first screen could be rendered."
    )
    st.write(f"Python runtime: {platform.python_version()}")
    st.write(f"Error: {type(exc).__name__}: {exc}")
    with st.expander("Startup traceback"):
        st.code(traceback.format_exc())
    raise
