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
    run_pipeline(inp, outp)
    df = pd.read_csv(outp)
    st.success("Done.")
    st.dataframe(df)
    st.download_button("Download results", data=df.to_csv(index=False), file_name="sites.csv", mime="text/csv")
else:
    st.info("Upload a CSV to start.")
