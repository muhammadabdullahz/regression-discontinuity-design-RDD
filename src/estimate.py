"""Regression discontinuity estimates for the CRA 80% tract-income cutoff."""
import pandas as pd
from rdrobust import rdrobust


def run_rd(t, y="y1", h=None, p=1, kernel="triangular", c=0.0):
    """Sharp RD, standard errors clustered by county. x = 80 - income %, treated if x > c."""
    d = t.dropna(subset=[y])
    kw = dict(c=0, p=p, kernel=kernel, bwselect="mserd", cluster=pd.factorize(d["county"])[0])
    if h is not None:
        kw["h"] = h
    return rdrobust(d[y].values, (d["x"] - c - 1e-6).values, **kw)   # 1e-6 puts x == c on the control side


def tidy(rd, label: str) -> dict:
    return {"label": label,
            "coef": float(rd.coef.iloc[0, 0]),
            "ci_lo": float(rd.ci.iloc[2, 0]), "ci_hi": float(rd.ci.iloc[2, 1]),   # robust CI
            "h": float(rd.bws.iloc[0, 0]),
            "n_left": int(rd.N_h[0]), "n_right": int(rd.N_h[1])}


def scale_effect(t: pd.DataFrame, coef: float, h: float) -> dict:
    ctrl = t[(t["x"] <= 0) & (t["x"] >= -h)]
    win = t[t["x"].abs() <= h]
    loans = coef / 1000 * win["tract_owner_occupied_units"].mean()
    avg_loan = ctrl["orig_amt"].sum() / ctrl["orig"].sum()
    return {"control_mean_y1": ctrl["y1"].mean(), "pct_of_control_mean": 100 * coef / ctrl["y1"].mean(),
            "extra_loans_per_tract": loans, "avg_loan_$": avg_loan, "extra_$_per_tract": loans * avg_loan}
