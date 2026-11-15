"""Step 11 (burn scars, step 5): a fresh exam. The same recipe on a fire it has never seen.

Fix C (look-alikes by score AND height) was designed after seeing Black Cove's mistakes,
so Black Cove is not a fair exam for it. Here every step runs unchanged on the Great Lakes
fire (Croatan National Forest, eastern NC, April 2023): flat, swampy coastal ground.

Rules fixed BEFORE looking at any burn pixel:
  - Answer key: the fire agencies' certified final outline (NIFC), not the MTBS one,
    because MTBS draws its outlines from the same kind of satellite score we are testing.
  - Photo pairs (one satellite each, taken from the step 7 list of clear photos):
        Landsat:    Apr 18 -> May 4, 2023
        Sentinel-2: Apr 10 -> May 10, 2023
  - Maps: the same five, nothing retuned: textbook, histogram, fix A, fix B, fix C.
Predictions written down first:
  1. Flat ground, so height should not matter: fix C about equal to fix A.
  2. Mostly evergreen plants, so little leaf-season shift: the plain cutoffs should work.
"""
import importlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

import fires
import hls
import terrain

step7 = importlib.import_module("07_find_fire_photos")
step8 = importlib.import_module("08_burn_maps")
step9 = importlib.import_module("09_grade_burn_maps")
step10 = importlib.import_module("10_ridge_check")

ROOT = Path(__file__).resolve().parents[1]
FIRE = "Great Lakes (Apr 2023), NIFC outline"
PAIRS = {
    "Landsat": {"satellite": "Landsat", "before": "2023-04-18", "after": "2023-05-04"},
    "Sentinel-2": {"satellite": "Sentinel-2", "before": "2023-04-10", "after": "2023-05-10"},
}
MAPS = step9.MAP_ORDER + [step10.FIX_C]  # textbook, histogram, fix A, fix B, fix C
KM2 = step8.KM2_PER_PIXEL


def run():
    """Build and grade all maps with the unchanged functions from steps 8, 9 and 10."""
    shape = fires.outline(FIRE)
    bbox = fires.box_around(shape)
    all_data = {name: step8.load_pair(bbox, pair) for name, pair in PAIRS.items()}
    band = all_data["Landsat"]["after"]["nir"]  # both satellites share one pixel grid
    inside = fires.outline_mask(shape, band)
    ring = fires.ring_mask(shape, band)
    height = terrain.height_like(band, bbox)

    all_maps, facts, rows = {}, [], []
    for name, d in all_data.items():
        plain = step8.make_maps(d)
        maps, groups, ring_normal = step9.build_maps(d, plain, ring)
        before = d["before"]["nbr"].values
        normal_c, _ = step10.lookalike_height_normal(before, height, d["dnbr"], d["usable"])
        with np.errstate(invalid="ignore"):
            maps[step10.FIX_C] = (d["dnbr"] - normal_c) > step9.EXTRA
        all_maps[name] = maps
        u = d["usable"]
        facts.append({
            "pair": name, "box usable": f"{u.mean():.0%}", "outline visible": f"{u[inside].mean():.0%}",
            "median change, whole box": round(float(np.median(d["dnbr"][u])), 3),
            "top of the pile": round(plain["peak"], 3), "histogram cutoff": round(plain["cutoffs"]["histogram"], 3),
            "normal change in the ring": round(ring_normal, 3),
            "look-alike groups, lowest": round(float(groups["typical change"].min()), 3),
            "look-alike groups, highest": round(float(groups["typical change"].max()), 3),
            **burned_share_of_groups(before, height, u, inside),
        })
        for m in MAPS:
            rows.append({"pair": name, "map": m, **step9.grade(maps[m], inside, u)})
    return {"data": all_data, "maps": all_maps, "inside": inside, "height": height,
            "facts": pd.DataFrame(facts), "scores": pd.DataFrame(rows), "bbox": bbox}


def burned_share_of_groups(before, height, usable, inside):
    """A check on the look-alike idea: how much of each group lies inside the outline?

    "Normal" is the middle value (median) of a group. If more than half of a group burned,
    its middle value IS a burned pixel, and the group can no longer say what unburned looks like.
    """
    score20, _ = step10.equal_count_bins(before, usable, step9.GROUPS)
    score10, _ = step10.equal_count_bins(before, usable, step10.SCORE_GROUPS)
    band5, _ = step10.equal_count_bins(height, usable, step10.HEIGHT_BANDS)
    out = {}
    for label, group in (("fix A groups", score20), ("fix C groups", score10 * step10.HEIGHT_BANDS + band5)):
        shares = np.array([inside[usable & (group == g)].mean() for g in np.unique(group[usable])])
        out[f"{label}: most-burned group"] = f"{shares.max():.0%}"
        out[f"{label}: groups over half burned"] = f"{(shares > 0.5).sum()} of {len(shares)}"
    return out


def both_fires(scores):
    """Side by side: the same five maps on Black Cove (from step 10's saved table) and Great Lakes."""
    black_cove = pd.read_csv(ROOT / "results" / "10_burn_scores_with_fix_c.csv").assign(fire="Black Cove")
    great_lakes = scores.assign(fire="Great Lakes")
    cols = ["fire", "pair", "map", "caught", "right", "F1"]
    return pd.concat([black_cove, great_lakes])[cols].reset_index(drop=True)


def plot_scores(scores, path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    for ax, (pair, d) in zip(axes, scores.groupby("pair", sort=False)):
        x = np.arange(len(d))
        ax.bar(x - 0.2, d["caught"], 0.4, color="#2b8cbe", label="caught (share of the outline flagged)")
        ax.bar(x + 0.2, d["right"], 0.4, color="#fdae61", label="right (share of flags inside the outline)")
        for xi, c, r in zip(x, d["caught"], d["right"]):
            ax.text(xi - 0.2, c + 0.02, f"{c:.0%}", ha="center", fontsize=9)
            ax.text(xi + 0.2, r + 0.02, f"{r:.0%}", ha="center", fontsize=9)
        ax.set_xticks(x, [m.replace(": ", ":\n").replace(" + ", "\n+ ") for m in d["map"]], fontsize=9)
        ax.set_ylim(0, 1.12)
        ax.set_title(f"{pair} pair ({PAIRS[pair]['before'][5:]} to {PAIRS[pair]['after'][5:]})")
    axes[0].set_ylabel("share")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=9)
    fig.suptitle("Great Lakes fire: the unchanged recipe, graded against the certified outline")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=130)
    return fig


def plot_outcomes(r, path):
    colors = ListedColormap(["#d7301f", "#fecc5c", "#2b8cbe"])  # caught, missed, false alarm
    inside = r["inside"]
    fig, axes = plt.subplots(2, 5, figsize=(19, 10.5))
    for row, (pair, maps) in zip(axes, r["maps"].items()):
        d = r["data"][pair]
        band = d["after"]["nir"]
        ext = step8.extent(band)
        for ax, name in zip(row, MAPS):
            flagged = maps[name] & d["usable"]
            outcome = np.full(inside.shape, np.nan)
            outcome[flagged & inside] = 0
            outcome[~flagged & inside & d["usable"]] = 1
            outcome[flagged & ~inside] = 2
            ax.imshow(np.clip(band.values / 0.4, 0, 1), cmap="gray", extent=ext)
            ax.imshow(np.where(d["usable"], np.nan, 1), cmap=ListedColormap(["white"]), extent=ext, alpha=0.6)
            ax.imshow(outcome, cmap=colors, vmin=0, vmax=2, extent=ext, interpolation="nearest")
            step8.draw_outline(ax, band, name=FIRE)
            ax.set_title(f"{pair} pair, {name}", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.legend(handles=[Patch(color="#d7301f", label="caught: flagged, inside the outline"),
                        Patch(color="#fecc5c", label="missed: inside the outline, not flagged"),
                        Patch(color="#2b8cbe", label="false alarm: flagged, outside the outline"),
                        Patch(facecolor="white", edgecolor="gray", label="cloud, shadow or water (not graded)")],
               loc="lower center", ncol=4, fontsize=10)
    fig.suptitle("Great Lakes fire: every burn map, colored by outcome (black line = certified outline)")
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=2.5)
    fig.savefig(path, dpi=110)
    return fig


def main():
    hls.login()
    figs, res = ROOT / "figures", ROOT / "results"
    # A first look in false color, same picture style as step 7.
    step7.plot_first_look(FIRE, PAIRS["Landsat"]["before"], PAIRS["Landsat"]["after"], "Landsat",
                          figs / "11_great_lakes_first_look.png")

    r = run()
    inside, height = r["inside"], r["height"]
    print(f"Outline {inside.sum() * KM2:.1f} km2 = {inside.mean():.0%} of the box. "
          f"Ground height in the box: {np.nanpercentile(height, 1):.0f} to {np.nanpercentile(height, 99):.0f} m "
          f"(middle 98% of pixels).")
    print("\nFacts about each pair")
    print(r["facts"].T.to_string(header=False))
    print("\nScores against the certified outline")
    print(r["scores"].to_string(index=False))
    r["scores"].to_csv(res / "11_great_lakes_scores.csv", index=False)
    r["facts"].to_csv(res / "11_great_lakes_pair_facts.csv", index=False)

    table = both_fires(r["scores"])
    table.to_csv(res / "11_both_fires.csv", index=False)

    plot_scores(r["scores"], figs / "11_great_lakes_scores.png")
    plot_outcomes(r, figs / "11_great_lakes_outcomes.png")
    print("\nSaved figures/11_great_lakes_first_look.png, 11_great_lakes_scores.png, 11_great_lakes_outcomes.png")


if __name__ == "__main__":
    main()
