from pathlib import Path

import pandas as pd

from src.build import build_tract, collapse_hmda, load_ffiec
from src.pull import pull_hmda

YEAR = 2023
FFIEC = "/content/drive/MyDrive/RDD/CensusFlatFile2023.csv"   # FFIEC census flat file, same year
CACHE = Path("data/processed/hmda_tract.parquet")

if CACHE.exists():
    hmda = pd.read_parquet(CACHE)
else:
    hmda = collapse_hmda(pull_hmda(YEAR))       # takes several minutes, then cached
    hmda.to_parquet(CACHE)

tract = build_tract(hmda, load_ffiec(FFIEC, YEAR))
tract.to_parquet("data/processed/tract.parquet")

print(tract.shape)
print(tract[["x", "y1_raw", "y1", "y2", "y3", "orig"]].describe().round(2))
print("tracts with zero home-purchase originations:", int((tract["orig"] == 0).sum()))

n_window = pd.DataFrame([{"window_pts": w, "tracts": int((tract.x.abs() <= w).sum()),
                          "below_80": int(((tract.x > 0) & (tract.x <= w)).sum()),
                          "at_or_above": int(((tract.x <= 0) & (tract.x >= -w)).sum())}
                         for w in [1, 2, 5]])
n_window.to_csv("outputs/n_by_window.csv", index=False)
print(n_window)
