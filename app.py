# app.py — drop-in replacement
# Streamlit UI for SPN Site Screener with a smart importer and an "offline" switch.

import os
import sys
import pathlib
import importlib.util
import streamlit as st
import pandas as pd

# ---------------- Smart importer: find spn_screener anywhere and import run_pipeline ----------------
def _find_run_pipeline():
    """
    Try to import run_pipeline from spn_screener.pipeline.
    If the package is nested (e.g., repo/subfolder/spn_screener), search for it and add to sys.path.
    As a last resort, load pipeline.py directly.
    """
    # 1) Normal import
    try:
        from spn_screener.pipeline import run_pipeline  # type: ignore
        return run_pipeline
    except Exception:
        pass

    base = pathlib.Path(__file__).resolve().parent

    # 2) Search for a folder named "spn_screener" anywhere under the repo
    try:
        for p in base.rglob("spn_screener"):
            if p.is_dir():
                parent = str(p.parent)
                if parent not in sys.path:
                    sys.path.insert(0, parent)
                try:
                    from spn_screener.pipeline import run_pipeline  # type: ignore
                    return run_pipeline
                except Exception:
                    continue
    except Exception:
        pass

    # 3) Fallback: locate pipeline.py directly and load it
    try:
        for pipeline_py in base.rglob("pipeline.py"):
            if pipeline_py.parent.name == "spn_screener":
                spec = importlib.util.spec_from_file_location("spn_screener.pipeline", pipeline_py)
                mod = importlib.util.module_from_spec(spec)  # type: ignore
                assert spec and spec.loader
                spec.loader.exec_module(mod)  # type: ignore
                return getattr(mod, "run_pipeline")
    except Exception as e:
        raise ImportError(f"Could not load pipeline.py directly: {e}")

    raise ImportError(
        "Could not find spn_screener.pipeline. "
        "Make sure your repo has a folder named 'spn_screener' with pipeline.py inside."
    )

RUN_PIPELINE = _find_run_pipeline()
# ---------------- End smart importer ----------------------------------------------------------------


# ---------------- Streamlit UI ----------------------------------------------------------------------
st.set_page_config(page_title="SPN Site Screener — NY", layout="wide")
st.title("SPN Site Screener — NY (Prototype)")

st.write(
    "Upload a CSV with columns: "
    "`address, city, state, zip, price_usd, acres, lat, lon, cleared_hint`."
)
st.caption(
    "Tip: If you get network/JSON errors, enable 'Skip online GIS lookups' to run offline. "
    "You’ll still get sizing and scoring, but wetlands/hosting-capacity will be treated as 0."
)

# Toggle to skip online GIS lookups (ArcGIS/DEC/NWI calls)
skip_remote = st.checkbox("Skip online GIS lookups (hosting capacity & wetlands)", value=False)
if skip_remote:
    os.environ["SPN_SKIP_REMOTE"] = "1"
else:
    os.environ.pop("SPN_SKIP_REMOTE", None)

uploaded = st.file_uploader(
    "Upload CSV", type=["csv"], accept_multiple_files=False, help="Drag-and-drop or click to select your CSV"
)

if uploaded:
    # Save upload to a temp path
    inp = "/tmp/in.csv"
    with open(inp, "wb") as f:
        f.write(uploaded.read())
    outp = "/tmp/out.csv"

    with st.spinner("Processing…"):
        try:
            RUN_PIPELINE(inp, outp)
        except Exception as e:
            st.error(
                "Processing error. If this mentions JSON/HTML or ArcGIS, try enabling "
                "'Skip online GIS lookups' above and rerun."
            )
            st.exception(e)
        else:
            try:
                df = pd.read_csv(outp)
            except Exception as e:
                st.error("Finished, but couldn’t read the output CSV.")
                st.exception(e)
            else:
                st.success("Done. Preview below — you can also download the full CSV.")
                st.dataframe(df, use_container_width=True)
                st.download_button(
                    "Download results (sites.csv)",
                    data=df.to_csv(index=False),
                    file_name="sites.csv",
                    mime="text/csv",
                )
else:
    st.info("Upload a CSV to start.")
# ---------------- End UI ----------------------------------------------------------------------------

