"""Step 2 (Week 2): water maps before and after Florence, and first flood maps.

Photos: Sept 6, 2018 (before) and Sept 18, 2018 (after), both Sentinel-2, Lumber River box.

Part A, textbook water indexes (FAILED here): NDWI and MNDWI with cutoff 0.
  The Lumber is a "blackwater" river: tea-colored from leaves. That water is darker in green than
  in shortwave infrared, so both indexes call most of the flood "land".
Part B, two near-infrared (NIR) rules that work for any water color:
  1. Dark-in-NIR: water = NIR < 0.10. Flood = water after that was not water before.
  2. NIR-drop:   flood = NIR fell to less than half (after / before < 0.5), not water before.
Pixels with cloud, cloud shadow or no data on EITHER day are left out.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

import hls

ROOT = Path(__file__).resolve().parents[1]
BEFORE, AFTER, SATELLITE = "2018-09-06", "2018-09-18", "Sentinel-2"
INDEX_CUTOFF = 0.0   # textbook: index above 0 = water
NIR_DARK = 0.10      # dark-in-NIR: below this = water (where the land pile starts rising)
NIR_RATIO = 0.5      # NIR-drop: after / before below this = flooded (NIR fell by at least half)
PIXEL_KM2 = 0.03 * 0.03  # one 30 m x 30 m pixel in square kilometres


def load_day(bbox, date):
    """Bands, cloud mask and usable-pixel mask for one day."""
    g = hls.find_photo(bbox, date, SATELLITE)
    print(f"{date}: {g['umm']['GranuleUR']}")
    bands = hls.read_reflectance(g, bbox, SATELLITE, ("red", "green", "blue", "nir", "swir1"))
    fmask = hls.read_band(hls.band_url(g, "Fmask"), bbox)
    return {"bands": bands, "fmask": fmask, "usable": hls.usable_mask(fmask),
            "nir": bands["nir"].values}


def rgb(bands):
    """Normal-color picture, brightened (most land reflects under 25% of light)."""
    return np.clip(np.dstack([bands[c].values for c in ("red", "green", "blue")]) / 0.25, 0, 1)


def km2(mask):
    return mask.sum() * PIXEL_KM2


def flood_dark_nir(before, after, use, cutoff=NIR_DARK):
    water_b = (before["nir"] < cutoff) & use
    water_a = (after["nir"] < cutoff) & use
    return water_b, water_a & ~water_b


def flood_nir_drop(before, after, use, ratio=NIR_RATIO, dark=NIR_DARK):
    water_b = (before["nir"] < dark) & use       # already water: a ratio there is just noise
    dropped = (after["nir"] / before["nir"] < ratio) & use
    return water_b, dropped & ~water_b


def flood_categories(water_b, flood, use):
    cats = np.zeros(use.shape, np.uint8)  # 0 = dry land
    cats[water_b] = 1                     # 1 = water already there before
    cats[flood] = 2                       # 2 = new flood water
    cats[~use] = 3                        # 3 = cloud / no data on either day
    return cats


def main():
    bbox = hls.STUDY_AREAS[hls.STUDY_AREA]
    hls.login()
    before, after = load_day(bbox, BEFORE), load_day(bbox, AFTER)
    # Same tile, so pixel (row, col) is the same spot on the ground in both photos.
    assert before["fmask"].shape == after["fmask"].shape
    assert np.allclose(before["fmask"].x, after["fmask"].x) and np.allclose(before["fmask"].y, after["fmask"].y)
    use = before["usable"] & after["usable"]
    print(f"Box pixels: {use.size:,}; usable on BOTH days: {use.mean():.0%}")

    # ---------- Part A: textbook indexes ----------
    rows = []
    for name, fn in (("NDWI", hls.ndwi), ("MNDWI", hls.mndwi)):
        wb = (fn(before["bands"]).values > INDEX_CUTOFF) & use
        wa = (fn(after["bands"]).values > INDEX_CUTOFF) & use
        rows.append({"method": f"{name} > 0", "water before km2": km2(wb), "water after km2": km2(wa),
                     "new flood km2": km2(wa & ~wb)})

    # ---------- Part B: NIR rules ----------
    wb_dark, flood_dark = flood_dark_nir(before, after, use)
    rows.append({"method": f"NIR < {NIR_DARK}", "water before km2": km2(wb_dark),
                 "water after km2": km2((after["nir"] < NIR_DARK) & use), "new flood km2": km2(flood_dark)})
    wb_drop, flood_drop = flood_nir_drop(before, after, use)
    rows.append({"method": f"NIR after/before < {NIR_RATIO}", "water before km2": km2(wb_drop),
                 "water after km2": km2(wb_drop | flood_drop), "new flood km2": km2(flood_drop)})
    table = pd.DataFrame(rows).round(1)
    print("\nWater and flood areas (only pixels usable on both days):")
    print(table.to_string(index=False))

    # Do the two NIR rules agree? Overlap = pixels both call flood, out of pixels either calls flood.
    both = flood_dark & flood_drop
    either = flood_dark | flood_drop
    overlap = both.sum() / either.sum()
    print(f"\nNIR rules agree: {km2(both):.1f} km2 flagged by both, {km2(either):.1f} by either "
          f"-> overlap {overlap:.0%}")
    print(f"  only dark-in-NIR: {km2(flood_dark & ~flood_drop):.1f} km2, only NIR-drop: {km2(flood_drop & ~flood_dark):.1f} km2")

    # Sanity check (NOT an accuracy test, same photo): NASA's Fmask water flag on the after photo.
    fm_water_a = ((after["fmask"].values & (1 << 5)) > 0) & use
    fm_water_b = ((before["fmask"].values & (1 << 5)) > 0) & use
    fm_flood = fm_water_a & ~fm_water_b
    print(f"\nSanity check vs Fmask water flag: Fmask new water {km2(fm_flood):.1f} km2; "
          f"share of it our rules also flag: dark-in-NIR {(fm_flood & flood_dark).sum() / fm_flood.sum():.0%}, "
          f"NIR-drop {(fm_flood & flood_drop).sum() / fm_flood.sum():.0%}")

    # How much does the answer depend on the cutoff? (There is no clean gap in the histogram.)
    sens = []
    for c in (0.05, 0.08, 0.10, 0.12, 0.15):
        sens.append({"rule": "dark-in-NIR", "cutoff": c, "new flood km2": km2(flood_dark_nir(before, after, use, c)[1])})
    for r in (0.3, 0.4, 0.5, 0.6, 0.7):
        sens.append({"rule": "NIR-drop", "cutoff": r, "new flood km2": km2(flood_nir_drop(before, after, use, r)[1])})
    sens = pd.DataFrame(sens).round({"new flood km2": 1})  # round areas only, keep cutoffs exact
    print("\nHow the flood area changes with the cutoff:")
    print(sens.to_string(index=False))

    out = ROOT / "results"
    table.to_csv(out / "02_water_areas.csv", index=False)
    sens.to_csv(out / "02_cutoff_sensitivity.csv", index=False)
    figs = ROOT / "figures"

    # --- Picture 1: photos and MNDWI before vs after (the textbook method) ---
    fig, ax = plt.subplots(2, 2, figsize=(12, 9))
    for col, (label, day, date) in enumerate((("before", before, BEFORE), ("after", after, AFTER))):
        ax[0, col].imshow(rgb(day["bands"]))
        ax[0, col].set_title(f"{date} ({label}): normal colors")
        m = hls.mndwi(day["bands"]).values
        im = ax[1, col].imshow(np.where(day["usable"], m, np.nan), cmap="RdBu", vmin=-0.6, vmax=0.6)
        ax[1, col].set_title(f"{date}: MNDWI\n(blue = water by textbook rule; clouds blank)")
    fig.colorbar(im, ax=ax[1, :], shrink=0.8, label="MNDWI")
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.savefig(figs / "02_before_after_mndwi.png", dpi=130, bbox_inches="tight")

    # --- Picture 2: NIR before vs after (the band that actually shows the flood) ---
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    for a, (label, day, date) in zip(ax, (("before", before, BEFORE), ("after", after, AFTER))):
        im = a.imshow(np.where(day["usable"], day["nir"], np.nan), cmap="gray", vmin=0, vmax=0.4)
        a.set_title(f"{date} ({label})\nnear-infrared: dark = water")
        a.set_xticks([]); a.set_yticks([])
    fig.colorbar(im, ax=ax, shrink=0.8, label="NIR reflectance")
    fig.savefig(figs / "02_nir_before_after.png", dpi=130, bbox_inches="tight")

    # --- Picture 3: histograms with cutoffs ---
    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    ax[0].hist(hls.mndwi(after["bands"]).values[use], bins=200, range=(-1, 1), color="gray")
    ax[0].axvline(INDEX_CUTOFF, color="crimson", ls="--"); ax[0].set_title("MNDWI, Sept 18 (cutoff 0)")
    ax[1].hist(after["nir"][use], bins=200, range=(0, 0.5), color="gray")
    ax[1].axvline(NIR_DARK, color="crimson", ls="--"); ax[1].set_title(f"NIR, Sept 18 (cutoff {NIR_DARK})")
    ax[2].hist((after["nir"] / before["nir"])[use], bins=200, range=(0, 2), color="gray")
    ax[2].axvline(NIR_RATIO, color="crimson", ls="--"); ax[2].set_title(f"NIR after / before (cutoff {NIR_RATIO})")
    for a in ax:
        a.set_yscale("log"); a.set_ylabel("pixels")
    fig.tight_layout(); fig.savefig(figs / "02_histograms.png", dpi=130)

    # --- Picture 4: three flood maps side by side ---
    colors = ["#f0f0f0", "#2b83ba", "#d7191c", "#9e9e9e"]
    wb_m = (hls.mndwi(before["bands"]).values > 0) & use
    flood_m = (hls.mndwi(after["bands"]).values > 0) & use & ~wb_m
    maps = [("MNDWI > 0 (textbook, failed)", wb_m, flood_m),
            (f"Dark-in-NIR (NIR < {NIR_DARK})", wb_dark, flood_dark),
            (f"NIR-drop (fell by half)", wb_drop, flood_drop)]
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.4))
    for a, (title, wb, fl) in zip(ax, maps):
        a.imshow(flood_categories(wb, fl, use), cmap=ListedColormap(colors), vmin=-0.5, vmax=3.5, interpolation="nearest")
        a.set_title(f"{title}\nnew flood water: {km2(fl):.1f} km²")
        a.set_xticks([]); a.set_yticks([])
    fig.legend(handles=[Patch(color=c, label=l) for c, l in zip(colors, [
        "dry land", "water before (river, ponds)", "new flood water", "cloud or no data (left out)"])],
        loc="lower center", ncol=4)
    fig.suptitle("Lumber River at Lumberton: water on Sept 18, 2018 that was not water on Sept 6")
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(figs / "02_flood_maps_compared.png", dpi=130)

    # Save the two NIR flood maps as map files for later steps (data/ is git-ignored).
    (ROOT / "data").mkdir(exist_ok=True)
    for tag, wb, fl in (("dark_nir", wb_dark, flood_dark), ("nir_drop", wb_drop, flood_drop)):
        after["fmask"].copy(data=flood_categories(wb, fl, use)).rio.to_raster(ROOT / "data" / f"02_flood_{tag}.tif")
    print("\nSaved figures/02_*.png, results/02_*.csv, data/02_flood_*.tif")


if __name__ == "__main__":
    main()
