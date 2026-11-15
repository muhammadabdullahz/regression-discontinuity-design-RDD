"""Collapse HMDA loans to one row per tract and merge with the FFIEC tract file."""
import numpy as np
import pandas as pd

COVS = ["tract_population", "tract_minority_population_percent",
        "tract_owner_occupied_units", "tract_one_to_four_family_homes"]
USECOLS = ["census_tract", "action_taken", "loan_purpose", "loan_amount"] + COVS
OUT = ["orig", "deny", "app", "orig_amt"]


def winsorize(s: pd.Series, lo: float = 0.01, hi: float = 0.99) -> pd.Series:
    a, b = s.quantile([lo, hi])
    return s.clip(a, b)


def collapse_hmda(path, chunksize: int = 500_000) -> pd.DataFrame:
    """One row per tract. Covariates come from all loans, outcomes from home-purchase loans."""
    cov_parts, out_parts = [], []
    for ch in pd.read_csv(path, usecols=USECOLS, dtype=str, chunksize=chunksize):
        ch = ch[ch["census_tract"].str.len() == 11]                  # drops "NA" tracts
        cov_parts.append(ch.groupby("census_tract")[COVS].first())
        hp = ch[ch["loan_purpose"] == "1"].copy()                    # home purchase
        act = pd.to_numeric(hp["action_taken"], errors="coerce")
        hp["orig"] = (act == 1).astype(int)                          # originated
        hp["deny"] = (act == 3).astype(int)                          # denied
        hp["app"] = act.isin([1, 2, 3]).astype(int)                  # reached a decision
        hp["orig_amt"] = pd.to_numeric(hp["loan_amount"], errors="coerce").where(hp["orig"] == 1, 0)
        out_parts.append(hp.groupby("census_tract")[OUT].sum())
    cov = pd.concat(cov_parts).groupby(level=0).first()
    out = pd.concat(out_parts).groupby(level=0).sum()
    t = cov.join(out).fillna({c: 0 for c in OUT})                    # no loans = 0, not missing
    t[COVS] = t[COVS].apply(pd.to_numeric, errors="coerce")
    return t.rename_axis("geoid").reset_index()


def load_ffiec(path, year: int) -> pd.DataFrame:
    """FFIEC census flat file, read by position: fields 1-5, 13 (income %), 15 (income level)."""
    raw = pd.read_csv(path, header=None, dtype=str)
    assert (raw[0] == str(year)).all(), "FFIEC file year does not match HMDA year"
    ref = pd.DataFrame({
        "geoid": raw[2].str.zfill(2) + raw[3].str.zfill(3) + raw[4].str.zfill(6),
        "income_pct": pd.to_numeric(raw[12], errors="coerce"),
        "indicator": pd.to_numeric(raw[14], errors="coerce"),
    })
    return ref[(ref["income_pct"] > 0) & (ref["indicator"] > 0)]     # 0 = not computed


def build_tract(hmda: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    assert ref["geoid"].is_unique, "split tracts in FFIEC file"
    t = ref.merge(hmda, on="geoid", how="inner")
    print(f"FFIEC tracts {len(ref)}, matched to HMDA {len(t)} ({100 * len(t) / len(ref):.1f}%)")

    t["x"] = 80 - t["income_pct"]                        # positive = below 80%
    t["D"] = (t["x"] > 0).astype(int)
    t["county"] = t["geoid"].str[:5]                     # for clustering
    t = t[t["tract_owner_occupied_units"] > 0].copy()    # need a denominator

    t["y1_raw"] = 1000 * t["orig"] / t["tract_owner_occupied_units"]   # loans per 1,000 owner-occ. units
    t["y1"] = winsorize(t["y1_raw"])
    t["y2"] = winsorize(np.log1p(t["orig_amt"]))                       # log(1 + dollars originated)
    t["y3"] = (t["deny"] / t["app"]).where(t["app"] > 0)               # denial rate

    assert t["geoid"].is_unique, "tract IDs not unique"
    assert (t["D"] == t["indicator"].isin([1, 2]).astype(int)).all(), "D != FFIEC income flag"
    assert len(t) > 50_000, "too few tracts; merge looks wrong"
    return t
