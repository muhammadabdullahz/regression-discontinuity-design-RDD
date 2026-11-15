import pandas as pd

from src.build import COVS
from src.estimate import run_rd, tidy

t = pd.read_parquet("data/processed/tract.parquet")
rows = []


def add(check, label, data=t, **kw):
    rows.append(tidy(run_rd(data, **kw), label) | {"check": check})


add("baseline", "baseline")

z = t.assign(**{c: (t[c] - t[c].mean()) / t[c].std() for c in COVS})   # covariates in standard deviations
for c in COVS:
    add("balance", c, data=z, y=c)

for inc in (70, 90):                                       # fake cutoffs, using one side of 80 only
    side = t[t["x"] > 0] if inc < 80 else t[t["x"] <= 0]
    add("placebo", f"placebo at {inc}%", data=side, c=80 - inc)

for p in (1, 2):
    for k in ("triangular", "uniform"):
        add("spec", f"order {p}, {k}", p=p, kernel=k)

for d in (0.5, 1, 2):
    add("donut", f"drop |x| < {d}", data=t[t["x"].abs() >= d])

for y in ("y1_raw", "y2", "y3"):
    add("outcome", y, y=y)

out = pd.DataFrame(rows)
out.to_csv("outputs/robustness.csv", index=False)
print(out[["check", "label", "coef", "ci_lo", "ci_hi", "h", "n_left", "n_right"]].round(2).to_string())
