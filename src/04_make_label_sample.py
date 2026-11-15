"""Step 4a: pick random spots to label, and save a NOAA airplane photo of each.

Why a mixed ("stratified") sample: flood covers only a few percent of the box. A plain random
sample of 300 spots would contain only a handful of flood spots, too few to grade the maps.
So we pick a fixed number from each group (below), then correct for the group sizes when scoring.

Groups (only pixels that were NOT water before and were cloud-free in the HLS photos):
  dark_nir   - dark-in-NIR map says flood                       100 spots
  drop_only  - only the NIR-drop map says flood                  50 spots
  radar_only - only the radar map says flood                     40 spots
  dry        - all three maps say dry                           110 spots
Only spots that a NOAA flight photographed (Sept 19-20) can be used.
The labeling page never shows which group a spot came from.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rioxarray
from pyproj import Transformer

import noaa

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "labels"
QUOTAS = {"dark_nir": 100, "drop_only": 50, "radar_only": 40, "dry": 110}
SEED = 42


def groups():
    """Group of every pixel, plus how many pixels each group has in the whole box."""
    dark = rioxarray.open_rasterio(ROOT / "data" / "02_flood_dark_nir.tif").squeeze(drop=True)
    drop = rioxarray.open_rasterio(ROOT / "data" / "02_flood_nir_drop.tif").squeeze(drop=True)
    cmp3 = rioxarray.open_rasterio(ROOT / "data" / "03_radar_vs_nir.tif").squeeze(drop=True)
    d, p = dark.values, drop.values
    radar_flood = np.isin(cmp3.values, (2, 3))   # 2 = radar only, 3 = both (radar and dark-in-NIR)
    eligible = (d != 3) & (d != 1) & (p != 1)     # cloud-free, not water before
    g = np.full(d.shape, "", object)
    g[eligible & (d == 0) & (p == 0) & ~radar_flood] = "dry"
    g[eligible & (d == 0) & (p == 0) & radar_flood] = "radar_only"
    g[eligible & (d == 0) & (p == 2)] = "drop_only"
    g[eligible & (d == 2)] = "dark_nir"
    return dark, g


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "chips").mkdir(exist_ok=True)
    grid, g = groups()
    to_ll = Transformer.from_crs(grid.rio.crs, 4326, always_xy=True)
    rng = np.random.default_rng(SEED)
    rows_out = []
    for name, quota in QUOTAS.items():
        rr, cc = np.nonzero(g == name)
        print(f"{name}: {len(rr):,} pixels in the box; need {quota} spots with a NOAA photo")
        got = tried = 0
        for i in rng.permutation(len(rr)):
            tried += 1
            lon, lat = to_ll.transform(float(grid.x[cc[i]]), float(grid.y[rr[i]]))
            res = noaa.chip(lon, lat)
            if res is None:
                continue
            img, day = res
            spot_id = f"s{len(rows_out):03d}"
            img.save(OUT / "chips" / f"{spot_id}.jpg", quality=88)
            rows_out.append({"id": spot_id, "group": name, "lat": lat, "lon": lon,
                             "row": int(rr[i]), "col": int(cc[i]), "noaa_flight": day,
                             "group_pixels": len(rr)})
            got += 1
            if got == quota:
                break
        print(f"  got {got} after trying {tried} random pixels "
              f"({got / tried:.0%} of tried spots had a NOAA photo)")
    df = pd.DataFrame(rows_out)
    df.to_csv(OUT / "sample.csv", index=False)
    print(f"\nSaved {len(df)} spots to data/labels/sample.csv and photo chips to data/labels/chips/")


if __name__ == "__main__":
    main()
