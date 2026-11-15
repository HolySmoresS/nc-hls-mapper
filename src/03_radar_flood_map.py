"""Step 3: our own radar flood map from Sentinel-1, compared with the near-infrared (NIR) maps.

Radar sends its own microwave pulse and listens for the echo, so clouds do not matter.
- Calm open water reflects the pulse away like a mirror: very dark (very negative dB).
- Water under trees can do the opposite: pulse bounces water -> trunk -> satellite, so it gets BRIGHTER.

Pictures: Sentinel-1A, orbit path 77, Sept 7 (before) and Sept 19 (after), 2018, cleaned up by
NASA's HyP3 service (src/radar.py) and lined up on the same 30 m grid as the HLS photos.

Rules:
- Radar open water = VV < -17 dB (where the land pile starts rising in the histogram).
- Radar flood = open water on Sept 19 that was not open water on Sept 7.
- "Brightened" = VV rose by more than 3 dB: a HINT of water under trees, not proof.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from pyproj import Transformer
from rasterio.enums import Resampling

import noaa
import radar

ROOT = Path(__file__).resolve().parents[1]
VV_WATER = -17.0       # dB: below this = open water
VV_BRIGHTEN = 3.0      # dB: rise bigger than this = "brightened"
PIXEL_KM2 = 0.03 * 0.03


def load_radar(template):
    """Both radar pictures, lined up pixel-for-pixel with the HLS grid of the template map."""
    out = {}
    for label in ("before", "after"):
        da = rioxarray.open_rasterio(radar.local_vv(label), masked=True).squeeze(drop=True)
        out[label] = da.rio.reproject_match(template, resampling=Resampling.bilinear).values
    return out


def km2(mask):
    return mask.sum() * PIXEL_KM2


def spot_check(cats_da, path, per_group=4, seed=0):
    """Show NOAA airplane photos at random spots of each kind (a quick look, NOT the full grade)."""
    to_ll = Transformer.from_crs(cats_da.rio.crs, 4326, always_xy=True)
    groups = {"NIR only": 1, "radar brightened": 4, "both": 3}
    rng = np.random.default_rng(seed)
    fig, ax = plt.subplots(len(groups), per_group, figsize=(3.5 * per_group, 3.5 * len(groups)))
    for a in ax.ravel():
        a.axis("off")
    for k, (name, code) in enumerate(groups.items()):
        rows, cols = np.nonzero(cats_da.values == code)
        got = 0
        for i in rng.permutation(len(rows))[:60]:  # try random spots until enough have a NOAA photo
            lon, lat = to_ll.transform(float(cats_da.x[cols[i]]), float(cats_da.y[rows[i]]))
            res = noaa.photo_at(lon, lat)
            if res is None:
                continue
            im, px, py, day = res
            a = ax[k, got]
            a.imshow(im)
            side = 30 / noaa.metres_per_pixel(lat)  # one 30 m pixel in photo pixels (about 30)
            a.add_patch(plt.Rectangle((px - side / 2, py - side / 2), side, side, fill=False, ec="yellow", lw=2))
            a.set_title(f"{name}\n{lat:.4f}, {lon:.4f} (NOAA {day[4:6]}/{day[6:8]})", fontsize=9)
            got += 1
            if got == per_group:
                break
    fig.suptitle("NOAA airplane photos at random spots; yellow square = one 30 m pixel")
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    radar.fetch_all()  # downloads only if missing
    # Step 2 saved its maps on the HLS grid: 0 dry, 1 water before, 2 new flood, 3 cloud/no data.
    dark = rioxarray.open_rasterio(ROOT / "data" / "02_flood_dark_nir.tif").squeeze(drop=True)
    drop = rioxarray.open_rasterio(ROOT / "data" / "02_flood_nir_drop.tif").squeeze(drop=True)
    vv = load_radar(dark)
    assert np.isfinite(vv["before"]).all() and np.isfinite(vv["after"]).all(), "radar has blank pixels in the box"

    water_b = vv["before"] < VV_WATER
    water_a = vv["after"] < VV_WATER
    flood_radar = water_a & ~water_b
    brightened = (vv["after"] - vv["before"]) > VV_BRIGHTEN

    optical_ok = dark.values != 3            # optical maps only exist where no cloud
    nir_dark = dark.values == 2
    nir_drop = drop.values == 2

    print(f"Radar open water: before {km2(water_b):.1f} km2, after {km2(water_a):.1f} km2")
    print(f"Radar new flood (whole box, clouds don't matter): {km2(flood_radar):.1f} km2")
    print(f"  of which under optical clouds: {km2(flood_radar & ~optical_ok):.1f} km2")
    print(f"Brightened by > {VV_BRIGHTEN} dB (hint of water under trees): {km2(brightened):.1f} km2")

    # Compare only where the optical maps exist.
    rows = []
    for name, nir in (("dark-in-NIR", nir_dark), ("NIR-drop", nir_drop)):
        both = (nir & flood_radar & optical_ok).sum()
        either = ((nir | flood_radar) & optical_ok).sum()
        rows.append({
            "NIR rule": name,
            "NIR flood km2": km2(nir),
            "radar flood km2 (same area)": km2(flood_radar & optical_ok),
            "both km2": both * PIXEL_KM2,
            "overlap (both / either)": both / either if either else np.nan,
            "share of NIR flood radar calls open water": (nir & water_a).sum() / nir.sum(),
            "share of NIR flood radar calls brightened": (nir & brightened).sum() / nir.sum(),
        })
    table = pd.DataFrame(rows).round(3)
    print("\nRadar vs NIR (cloud-free pixels only):")
    print(table.to_string(index=False))

    # Median radar brightness for each optical category: what does radar "see" in NIR-flood pixels?
    med = []
    for name, m in (("dry land", dark.values == 0), ("water before", dark.values == 1),
                    ("NIR flood (dark-in-NIR)", nir_dark)):
        med.append({"optical category": name, "VV before dB": np.median(vv["before"][m]),
                    "VV after dB": np.median(vv["after"][m])})
    med = pd.DataFrame(med).round(1)
    print("\nMedian radar brightness by optical category:")
    print(med.to_string(index=False))

    out = ROOT / "results"
    table.to_csv(out / "03_radar_vs_nir.csv", index=False)
    med.to_csv(out / "03_radar_by_category.csv", index=False)
    figs = ROOT / "figures"

    # Picture 1: radar before and after
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    for a, label, date in zip(ax, ("before", "after"), ("Sept 7", "Sept 19")):
        im = a.imshow(vv[label], cmap="gray", vmin=-25, vmax=0)
        a.set_title(f"Sentinel-1 radar, {date}, 2018 ({label})\ndark = calm open water")
        a.set_xticks([]); a.set_yticks([])
    fig.colorbar(im, ax=ax, shrink=0.8, label="VV brightness (dB)")
    fig.savefig(figs / "03_radar_before_after.png", dpi=130, bbox_inches="tight")

    # Picture 2: radar vs NIR agreement map
    cats = np.zeros(nir_dark.shape, np.uint8)       # 0 neither
    cats[nir_dark & ~flood_radar] = 1               # 1 NIR only
    cats[flood_radar & ~nir_dark] = 2               # 2 radar only
    cats[nir_dark & flood_radar] = 3                # 3 both
    cats[brightened & (cats == 0)] = 4              # 4 radar brightened (hint)
    colors = ["#f0f0f0", "#d7191c", "#2b83ba", "#7b3294", "#fdae61"]
    labels = [f"neither", f"NIR only ({km2(cats == 1):.1f} km²)", f"radar open water only ({km2(cats == 2):.1f} km²)",
              f"both ({km2(cats == 3):.1f} km²)", f"radar brightened, maybe water under trees ({km2(cats == 4):.1f} km²)"]
    fig, ax = plt.subplots(figsize=(10, 7.8))
    ax.imshow(cats, cmap=ListedColormap(colors), vmin=-0.5, vmax=4.5, interpolation="nearest")
    ax.set_title("New flood water: dark-in-NIR (HLS, Sept 18) vs radar (Sentinel-1, Sept 19)")
    ax.legend(handles=[Patch(color=c, label=l) for c, l in zip(colors, labels)], loc="lower left", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(figs / "03_radar_vs_nir_map.png", dpi=130)

    cats_da = dark.copy(data=cats)
    cats_da.rio.to_raster(ROOT / "data" / "03_radar_vs_nir.tif")

    # Picture 3: what the NOAA airplane photos show at random spots of each kind
    spot_check(cats_da, figs / "03_noaa_spot_check.png")
    print("\nSaved figures/03_*.png, results/03_*.csv, data/03_radar_vs_nir.tif")


if __name__ == "__main__":
    main()
