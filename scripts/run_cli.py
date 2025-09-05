import argparse, os, json
from spn_screener.pipeline import run_pipeline

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input CSV with listings")
    ap.add_argument("--out", dest="out", required=True, help="Output CSV")
    ap.add_argument("--geo", dest="geo", required=False, help="(optional) Output GeoJSON – not implemented in v0.1")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    run_pipeline(args.inp, args.out)
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
