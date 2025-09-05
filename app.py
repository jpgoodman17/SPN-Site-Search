
# --- Smart importer: find spn_screener anywhere and import run_pipeline ---
import os, sys, pathlib, importlib.util

def _find_run_pipeline():
    # 1) Try the normal import
    try:
        from spn_screener.pipeline import run_pipeline  # noqa: F401
        return run_pipeline
    except Exception:
        pass

    base = pathlib.Path(__file__).resolve().parent

    # 2) Search the repo for a folder called "spn_screener"
    for p in base.rglob("spn_screener"):
        if p.is_dir():
            parent = str(p.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
            try:
                from spn_screener.pipeline import run_pipeline  # noqa: F401
                return run_pipeline
            except Exception:
                continue

    # 3) Fallback: load pipeline.py directly if found
    for pipeline_py in base.rglob("pipeline.py"):
        if pipeline_py.parent.name == "spn_screener":
            spec = importlib.util.spec_from_file_location("spn_screener.pipeline", pipeline_py)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(mod)
            return getattr(mod, "run_pipeline")

    raise ImportError("Could not find spn_screener.pipeline. Check that your repo has a 'spn_screener' folder with pipeline.py inside.")

RUN_PIPELINE = _find_run_pipeline()
# --- End smart importer ---


import streamlit as st
import pandas as pd
# Try importing the package. If it's nested (e.g., in spn_site_screener_v0_1/), adjust sys.path.
import os, sys

def _ensure_pkg_on_path():
    base = os.path.dirname(__file__)
    # Where the 'spn_screener' folder might be
    candidates = [
        os.path.join(base, "spn_screener"),                                # repo root
        os.path.join(base, "spn_site_screener_v0_1", "spn_screener"),      # nested folder
    ]
    for c in candidates:
        if os.path.isdir(c):
            parent = os.path.dirname(c)
            if parent not in sys.path:
                sys.path.insert(0, parent)
            return

_ensure_pkg_on_path()

from spn_screener.pipeline import run_pipeline

st.title("SPN Site Screener — NY (Prototype)")

uploaded = st.file_uploader("Upload CSV (address, city, state, zip, price_usd, acres, lat, lon, cleared_hint)", type=["csv"])
if uploaded:
    inp = "/tmp/in.csv"
    with open(inp, "wb") as f: f.write(uploaded.read())
    outp = "/tmp/out.csv"
    RUN_PIPELINE(inp, outp)
    df = pd.read_csv(outp)
    st.success("Done.")
    st.dataframe(df)
    st.download_button("Download results", data=df.to_csv(index=False), file_name="sites.csv", mime="text/csv")
else:
    st.info("Upload a CSV to start.")
