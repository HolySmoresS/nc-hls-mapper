"""The "clues" (features) a machine-learning model gets for each pixel of the Lumber River box.

21 clues per pixel, all on the same 30 m HLS grid:
- 6 color bands after the storm (Sept 18 HLS): blue, green, red, nir, swir1, swir2
- the same 6 bands before (Sept 6 HLS)
- 4 water indexes: NDWI and MNDWI, before and after
- 2 change clues: NIR after / before, SWIR1 after / before
- 3 radar clues (Sentinel-1 VV): before (Sept 7), after (Sept 19), change (after - before)
The whole stack is saved once to data/06_features.npz (git-ignored) so later runs are fast.
"""
from pathlib import Path

import numpy as np
import rioxarray
from rasterio.enums import Resampling

import hls
import radar

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "06_features.npz"
BEFORE, AFTER, SATELLITE = "2018-09-06", "2018-09-18", "Sentinel-2"
BAND_NAMES = ("blue", "green", "red", "nir", "swir1", "swir2")


def template():
    """Step 2's flood map: defines the grid. Values: 0 dry, 1 water before, 2 flood, 3 cloud/no data."""
    return rioxarray.open_rasterio(ROOT / "data" / "02_flood_dark_nir.tif").squeeze(drop=True)


def build():
    """Read everything and compute the 21 clues. Takes a minute or two (reads from NASA's cloud)."""
    hls.login()
    bbox = hls.STUDY_AREAS[hls.STUDY_AREA]
    grid = template()
    f = {}
    for tag, date in (("after", AFTER), ("before", BEFORE)):
        g = hls.find_photo(bbox, date, SATELLITE)
        bands = hls.read_reflectance(g, bbox, SATELLITE, BAND_NAMES)
        assert bands["nir"].shape == grid.shape, "HLS photo is not on the same grid as step 2"
        for b in BAND_NAMES:
            f[f"{b}_{tag}"] = bands[b].values
        f[f"ndwi_{tag}"] = hls.ndwi(bands).values
        f[f"mndwi_{tag}"] = hls.mndwi(bands).values
    f["nir_ratio"] = f["nir_after"] / f["nir_before"]
    f["swir1_ratio"] = f["swir1_after"] / f["swir1_before"]
    for tag in ("before", "after"):
        da = rioxarray.open_rasterio(radar.local_vv(tag), masked=True).squeeze(drop=True)
        f[f"vv_{tag}"] = da.rio.reproject_match(grid, resampling=Resampling.bilinear).values
    f["vv_change"] = f["vv_after"] - f["vv_before"]
    f = {k: v.astype("float32") for k, v in f.items()}
    np.savez_compressed(CACHE, **f)
    return f


def load():
    """The clue stack as {name: 2-D array}; built and saved the first time."""
    if CACHE.exists():
        with np.load(CACHE) as z:
            return {k: z[k] for k in z.files}
    return build()


if __name__ == "__main__":
    f = load()
    print(f"{len(f)} clues, grid {next(iter(f.values())).shape}")
    for k, v in f.items():
        print(f"  {k:<14} median {np.nanmedian(v):8.3f}")
