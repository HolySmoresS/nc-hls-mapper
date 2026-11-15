"""Step 8 (burn scars, step 2): burn maps for the Black Cove Complex from two pairs of photos.

The burn version of step 2 for the floods:
  1. NBR (Normalized Burn Ratio) before and after the fire,
  2. dNBR = NBR before - NBR after (a big positive number means "burned"),
  3. a cutoff, then a burn map.
We do it twice and compare:
  - "April" pair: Sentinel-2 Mar 11 vs Sentinel-2 Apr 12 (after the fire stopped; trees leafing out)
  - "March 26" pair: Landsat Mar 18 vs Landsat Mar 26 (perfectly clear, but the fire was still growing)
Each pair uses ONE satellite, so a change comes from the ground, not from a camera change.
Each pair gets two cutoffs: the textbook one (0.10) and one read from the histogram.
Both cutoffs are fixed WITHOUT looking at the official outline, so the outline stays a fair judge.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

import fires
import hls

ROOT = Path(__file__).resolve().parents[1]
FIRE = "Black Cove Complex (Mar 2025)"
PAIRS = {
    "April": {"satellite": "Sentinel-2", "before": "2025-03-11", "after": "2025-04-12"},
    "March 26": {"satellite": "Landsat", "before": "2025-03-18", "after": "2025-03-26"},
}
TEXTBOOK_CUTOFF = 0.10  # standard severity table (Key and Benson): dNBR above +0.10 = burned
KM2_PER_PIXEL = 30 * 30 / 1e6


def load_photo(bbox, date, satellite):
    """NBR for one photo, plus a mask of pixels we can trust (no cloud, no shadow, not water)."""
    g = hls.find_photo(bbox, date, satellite)
    fmask = hls.read_band(hls.band_url(g, "Fmask"), bbox)
    bands = hls.read_reflectance(g, bbox, satellite, names=("nir", "swir2"))
    nbr = hls.nbr(bands)
    usable = hls.usable_mask(fmask) & ((fmask.values & hls.FMASK_WATER_BIT) == 0) & np.isfinite(nbr.values)
    return {"nbr": nbr, "usable": usable, "nir": bands["nir"]}


def load_pair(bbox, pair):
    """Both photos of a pair and their difference. Pixels unusable on either day are blank (NaN)."""
    before = load_photo(bbox, pair["before"], pair["satellite"])
    after = load_photo(bbox, pair["after"], pair["satellite"])
    usable = before["usable"] & after["usable"]
    dnbr = np.where(usable, before["nbr"].values - after["nbr"].values, np.nan)
    return {"before": before, "after": after, "usable": usable, "dnbr": dnbr}


def make_maps(data):
    """Two burn maps per pair: textbook cutoff and histogram (triangle) cutoff."""
    values = data["dnbr"][data["usable"]]
    cutoff, peak = fires.triangle_cutoff(values)
    with np.errstate(invalid="ignore"):  # blank pixels compare as False, which is what we want
        maps = {"textbook": data["dnbr"] > TEXTBOOK_CUTOFF, "histogram": data["dnbr"] > cutoff}
    return {"peak": peak, "cutoffs": {"textbook": TEXTBOOK_CUTOFF, "histogram": cutoff}, "maps": maps}


def area_table(all_data, all_maps):
    rows = []
    for name, data in all_data.items():
        m = all_maps[name]
        for kind in ("textbook", "histogram"):
            rows.append({
                "pair": name,
                "cutoff": kind,
                "dNBR cutoff": round(m["cutoffs"][kind], 3),
                "pile peak": round(m["peak"], 3),
                "burned km2": round(m["maps"][kind].sum() * KM2_PER_PIXEL, 1),
                "box usable": f"{data['usable'].mean():.0%}",
            })
    return pd.DataFrame(rows)


def overlap(a, b, usable):
    """How much two burn maps agree, counted only where BOTH pairs could see the ground."""
    a, b = a & usable, b & usable
    both, either = (a & b).sum(), (a | b).sum()
    km2 = lambda mask: round(float(mask.sum() * KM2_PER_PIXEL), 1)  # plain numbers print more cleanly
    return {"both km2": km2(a & b), "only first km2": km2(a & ~b), "only second km2": km2(b & ~a),
            "overlap": round(float(both / either), 2)}


def extent(band):
    x, y = band.x.values, band.y.values
    return (x.min(), x.max(), y.min(), y.max())


def draw_outline(ax, band, color="black"):
    from pyproj import Transformer

    t = Transformer.from_crs("EPSG:4326", band.rio.crs, always_xy=True)
    shape = fires.outline(FIRE)
    for piece in getattr(shape, "geoms", [shape]):
        ax.plot(*t.transform(*piece.exterior.xy), color=color, linewidth=1)


def plot_nbr(all_data, path):
    """Rows = pairs. Columns = NBR before, NBR after, and the change (dNBR)."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for row, (name, d) in zip(axes, all_data.items()):
        ext = extent(d["before"]["nir"])
        for ax, when in zip(row[:2], ("before", "after")):
            im1 = ax.imshow(np.where(d[when]["usable"], d[when]["nbr"].values, np.nan), cmap="YlGn",
                            vmin=-0.2, vmax=0.7, extent=ext)
            ax.set_title(f"{name} pair: NBR {when} ({PAIRS[name][when]})", fontsize=10)
        im2 = row[2].imshow(d["dnbr"], cmap="RdBu_r", vmin=-0.5, vmax=0.5, extent=ext)
        row[2].set_title(f"{name} pair: change (before - after)", fontsize=10)
        for ax in row:
            ax.set_facecolor("lightgray")  # clouds, shadows and water show as gray
            ax.set_xticks([])
            ax.set_yticks([])
        for ax in row[:2]:  # a color bar on every panel keeps the three pictures the same size
            fig.colorbar(im1, ax=ax, fraction=0.04, label="NBR (greener = more alive)")
        fig.colorbar(im2, ax=row[2], fraction=0.04, label="dNBR (red = score fell)")
    fig.suptitle("Burn score before and after, and its change (gray = cloud, shadow or water)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    return fig


def plot_histograms(all_data, all_maps, path):
    """How many pixels changed by how much, with both cutoffs marked."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, (name, d) in zip(axes, all_data.items()):
        m = all_maps[name]
        ax.hist(d["dnbr"][d["usable"]], bins=np.arange(-0.7, 0.8, 0.01), color="gray")
        ax.set_yscale("log")  # each step up the side is 10x more pixels, so the small burn tail stays visible
        ax.axvline(m["cutoffs"]["textbook"], color="tab:blue", linestyle="--",
                   label=f"textbook cutoff {m['cutoffs']['textbook']:+.2f}")
        ax.axvline(m["cutoffs"]["histogram"], color="tab:red",
                   label=f"histogram cutoff {m['cutoffs']['histogram']:+.3f}")
        ax.axvline(m["peak"], color="black", linestyle=":", label=f"top of the pile {m['peak']:+.3f}")
        ax.set_title(f"{name} pair")
        ax.set_xlabel("dNBR (right = burn score fell)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("number of pixels (each step = 10x)")
    fig.suptitle("Change in burn score for every usable pixel in the box")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    return fig


def plot_maps(all_data, all_maps, path):
    """Four burn maps: rows = pairs, columns = cutoffs. Official outline drawn in black."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 10))
    red = ListedColormap(["#d7301f"])
    for row, (name, d) in zip(axes, all_data.items()):
        band = d["after"]["nir"]
        ext = extent(band)
        for ax, kind in zip(row, ("textbook", "histogram")):
            m = all_maps[name]
            ax.imshow(np.clip(band.values / 0.4, 0, 1), cmap="gray", extent=ext)  # the after photo as a backdrop
            ax.imshow(np.where(d["usable"], np.nan, 1), cmap=ListedColormap(["#74a9cf"]), extent=ext, alpha=0.7)
            ax.imshow(np.where(m["maps"][kind], 1, np.nan), cmap=red, extent=ext)
            draw_outline(ax, band)
            ax.set_title(f"{name} pair, {kind} cutoff (dNBR > {m['cutoffs'][kind]:+.3f})\n"
                         f"{m['maps'][kind].sum() * KM2_PER_PIXEL:.1f} km$^2$ flagged", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle("Burn maps (red = flagged as burned, blue = cloud/shadow/water, black line = official outline)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    return fig


def save_tif(array, like, path):
    """Save a map as a GeoTIFF (an image file that remembers where on Earth each pixel is)."""
    like.copy(data=array.astype("float32")).rio.to_raster(path)


def main():
    hls.login()
    bbox = fires.box_around(fires.outline(FIRE))
    all_data = {name: load_pair(bbox, pair) for name, pair in PAIRS.items()}
    all_maps = {name: make_maps(d) for name, d in all_data.items()}

    for name, d in all_data.items():
        u = d["usable"]
        print(f"{name} pair: median NBR before {np.median(d['before']['nbr'].values[u]):.3f}, "
              f"after {np.median(d['after']['nbr'].values[u]):.3f}, median change {np.median(d['dnbr'][u]):+.3f}")

    table = area_table(all_data, all_maps)
    print("\nBurned area by pair and cutoff")
    print(table.to_string(index=False))
    (ROOT / "results").mkdir(exist_ok=True)
    table.to_csv(ROOT / "results" / "08_burn_areas.csv", index=False)

    both_usable = all_data["April"]["usable"] & all_data["March 26"]["usable"]
    agree = overlap(all_maps["April"]["maps"]["histogram"], all_maps["March 26"]["maps"]["histogram"], both_usable)
    print("\nApril map vs March 26 map (histogram cutoffs, where both pairs are usable):", agree)
    pd.DataFrame([agree]).to_csv(ROOT / "results" / "08_pair_overlap.csv", index=False)

    figs = ROOT / "figures"
    plot_nbr(all_data, figs / "08_nbr_before_after.png")
    plot_histograms(all_data, all_maps, figs / "08_histograms.png")
    plot_maps(all_data, all_maps, figs / "08_burn_maps_compared.png")
    print("\nSaved figures/08_nbr_before_after.png, 08_histograms.png, 08_burn_maps_compared.png")

    # Keep the change maps and the burn maps for the grading step (data/ is git-ignored).
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    for name, d in all_data.items():
        key = name.lower().replace(" ", "")
        like = d["after"]["nir"]
        save_tif(d["dnbr"], like, data_dir / f"08_dnbr_{key}.tif")
        for kind, burned in all_maps[name]["maps"].items():
            save_tif(np.where(d["usable"], burned, np.nan), like, data_dir / f"08_burn_{key}_{kind}.tif")
    print("Saved change maps and burn maps to data/")


if __name__ == "__main__":
    main()
