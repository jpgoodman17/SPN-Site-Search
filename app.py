# app.py — robust importer + simple UI + diagnostics
import os, sys, pathlib, importlib.util
import streamlit as st
import pandas as pd

st.set_page_config(page_title="SPN Site Screener — NY", layout="wide")
st.title("SPN Site Screener — NY (Prototype)")

# ---------------- Robust importer ----------------
def _load_run_pipeline():
    """
    Try multiple ways to load run_pipeline:
      1) Normal import from spn_screener.pipeline
      2) Add repo root to sys.path and try again
      3) Search for 'spn_screener' anywhere under repo and add its parent
      4) Directly load spn_screener/pipeline.py if the file exists
      5) As a last resort, search for any pipeline.py inside any 'spn_screener' dir and load it
    """
    # 0) Figure out repo root (directory containing this app.py)
    base = pathlib.Path(__file__).resolve().parent

    # Strategy 1: normal import
    try:
        from spn_screener.pipeline import run_pipeline
        return run_pipeline
    except Exception as e1:
        err1 = str(e1)

    # Strategy 2: add repo root to sys.path
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    try:
        from spn_screener.pipeline import run_pipeline
        return run_pipeline
    except Exception as e2:
        err2 = str(e2)

    # Strategy 3: search for a folder named "spn_screener" and add its parent to sys.path
    try:
        for p in base.rglob("spn_screener"):
            if p.is_dir():
                parent = str(p.parent)
                if parent not in sys.path:
                    sys.path.insert(0, parent)
                try:
                    from spn_screener.pipeline import run_pipeline
                    return run_pipeline
                except Exception:
                    continue
    except Exception as e3:
        err3 = str(e3)
    else:
        err3 = "(searched, none worked)"

    # Strategy 4: direct load if repo-root path exists
    direct = base / "spn_screener" / "pipeline.py"
    if direct.exists():
        try:
            spec = importlib.util.spec_from_file_location("spn_screener.pipeline", direct)
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore
            return getattr(mod, "run_pipeline")
        except Exception as e4:
            err4 = str(e4)
    else:
        err4 = f"{direct} does not exist"

    # Strategy 5: last resort — find any spn_screener/**/pipeline.py and load it
    try:
        for pipeline_py in base.rglob("pipeline.py"):
            if pipeline_py.parent.name == "spn_screener":
                spec = importlib.util.spec_from_file_location("spn_screener.pipeline", pipeline_py)
                mod = importlib.util.module_from_spec(spec)  # type: ignore
                assert spec and spec.loader
                spec.loader.exec_module(mod)  # type: ignore
                return getattr(mod, "run_pipeline")
    except Exception as e5:
        err5 = str(e5)
    else:
        err5 = "(searched, none found or load failed)"

    # If we get here, surface helpful diagnostics in the UI
    details = {
        "cwd": os.getcwd(),
        "app_dir": str(base),
        "sys.path_head": sys.path[:5],
        "err1_normal_import": err1,
        "err2_with_base_on_syspath": err2,
        "err3_search_add_parent": err3,
        "err4_direct_load_repo_root": err4,
        "err5_last_resort_search": err5,
        "repo_tree_snippet": _list_tree(base, depth=2),
    }
    st.error("Could not find/load spn_screener.pipeline. See diagnostics below.")
    st.json(details)
    raise ImportError("spn_screener.pipeline not found")

def _list_tree(root: pathlib.Path, depth=2):
    """Return a small dict of the top-level repo tree to help debug layout."""
    def walk(p: pathlib.Path, d: int):
        if d < 0: return None
        if not p.exists(): return None
        if p.is_file(): return "file"
        out = {}
        try:
            for child in sorted(p.iterdir()):
                if child.name.startswith("."): 
                    continue
                if child.is_dir():
                    out[child.name] = walk(child, d-1)
                else:
                    out[child.name] = "file"
        except Exception:
            pass
        return out
    return walk(root, depth)

RUN_PIPELINE = _load_run_pipeline()
# ---------------- End importer ----------------

st.write(
    "Upload a CSV with columns: "
    "`address, city, state, zip, price_usd, acres, lat, lon, cleared_hint`."
)
st.caption(
    "Tip: If you get network/JSON errors, enable 'Skip online GIS lookups' to run offline. "
    "You’ll still get sizing/scoring, but wetlands/hosting-capacity will be treated as 0."
)

skip_remote = st.checkbox("Skip online GIS lookups (hosting capacity & wetlands)", value=False)
if skip_remote:
    os.environ["SPN_SKIP_REMOTE"] = "1"
else:
    os.environ.pop("SPN_SKIP_REMOTE", None)

uploaded = st.file_uploader("Upload CSV", type=["csv"], help="Drag-and-drop or click to select your CSV")

if uploaded:
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
