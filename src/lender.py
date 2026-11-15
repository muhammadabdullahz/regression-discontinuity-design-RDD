"""Home-purchase originations per tract, split by lender type (bank vs. other)."""
import pandas as pd


def lender_split(lar_path, ts_path, chunksize=500_000) -> pd.DataFrame:
    ts = pd.read_csv(ts_path, usecols=["lei", "agency_code"], dtype=str)
    banks = set(ts.loc[ts["agency_code"].isin(["1", "2", "3"]), "lei"])      # OCC, FRB, FDIC filers
    parts = []
    for ch in pd.read_csv(lar_path, usecols=["census_tract", "lei", "action_taken", "loan_purpose"],
                          dtype=str, chunksize=chunksize):
        ch = ch[(ch["loan_purpose"] == "1") & (ch["action_taken"] == "1")].copy()   # purchase originations
        ch["orig_bank"] = ch["lei"].isin(banks).astype(int)
        ch["orig_other"] = 1 - ch["orig_bank"]
        parts.append(ch.groupby("census_tract")[["orig_bank", "orig_other"]].sum())
    return pd.concat(parts).groupby(level=0).sum().rename_axis("geoid").reset_index()
