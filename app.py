import streamlit as st
import pandas as pd
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
