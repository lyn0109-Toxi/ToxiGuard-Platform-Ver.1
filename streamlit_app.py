from __future__ import annotations

import platform
import importlib
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


def _run_app() -> None:
    module_name = "toxiguard_platform.app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


try:
    _run_app()
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
