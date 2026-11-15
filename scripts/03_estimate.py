import pandas as pd

from src.estimate import run_rd, scale_effect, tidy

tract = pd.read_parquet("data/processed/tract.parquet")
rd = run_rd(tract)
res = tidy(rd, "baseline y1")
res.update(scale_effect(tract, res["coef"], res["h"]))

pd.DataFrame([res]).to_csv("outputs/results.csv", index=False)
print(rd)
for k, v in res.items():
    print(f"{k:22s} {v:.3f}" if isinstance(v, float) else f"{k:22s} {v}")
