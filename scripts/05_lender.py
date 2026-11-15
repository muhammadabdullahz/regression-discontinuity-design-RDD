import pandas as pd

from src.build import winsorize
from src.estimate import run_rd, tidy
from src.lender import lender_split
from src.pull import pull_hmda

tract = pd.read_parquet("data/processed/tract.parquet")
split = lender_split(pull_hmda(2023, "lar"), pull_hmda(2023, "ts"))
t = tract.merge(split, on="geoid", how="left").fillna({"orig_bank": 0, "orig_other": 0})
assert (t["orig_bank"] + t["orig_other"] == t["orig"]).all(), "lender split does not add up to total originations"

u = t["tract_owner_occupied_units"]
t["y1_bank"] = winsorize(1000 * t["orig_bank"] / u, 0, 0.99)     # loans per 1,000 owner-occupied units
t["y1_other"] = winsorize(1000 * t["orig_other"] / u, 0, 0.99)
t.to_parquet("data/processed/tract_lender.parquet")

rows = []
for y, label in [("y1_bank", "Banks (OCC/FRB/FDIC filers)"), ("y1_other", "All other filers")]:
    r = tidy(run_rd(t, y), label)
    m = t[(t["x"] <= 0) & (t["x"] >= -r["h"])][y].mean()          # mean just above 80%
    rows.append(r | {"mean_above": m, "pct": 100 * r["coef"] / m,
                     "pct_lo": 100 * r["ci_lo"] / m, "pct_hi": 100 * r["ci_hi"] / m})
out = pd.DataFrame(rows)
out.to_csv("outputs/lender.csv", index=False)
print(out.round(2).to_string())
