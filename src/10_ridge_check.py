"""Step 10 (burn scars, step 4): test the guess that late green-up on high ground fools the April map.

Step 9 found that the two leaf-season fixes paint false alarms along the mountain ridges.
The guess: higher ground greens up later in spring, so on April 12 the ridges had not leafed
out, and "greened up less than normal" looked like a burn.

Plan, written down before looking at any result:
  Test 1: on UNBURNED land, does the April change climb steadily with height?
  Test 2: is fix A's false-alarm rate higher on high ground?
  Rival explanation: the way a slope faces (sun angle changed between March and April).
  Fix C: look-alike groups by burn score before the fire AND height (10 x 5 groups),
         same rule as before: burned = the score fell 0.10 more than normal.
Honest warning: fix C was designed after seeing where the mistakes were, so the official
outline is not a perfectly fresh exam for it.
"""
import importlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import fires
import hls
import terrain

step8 = importlib.import_module("08_burn_maps")
step9 = importlib.import_module("09_grade_burn_maps")

ROOT = Path(__file__).resolve().parents[1]
SCORE_GROUPS, HEIGHT_BANDS = 10, 5
FIX_A, FIX_C = "fix A: look-alikes", "fix C: look-alikes + height"


def equal_count_bins(values, where, n):
    """Sort pixels into n bins that each hold the same number of pixels. Returns bin number and edges."""
    edges = np.quantile(values[where], np.linspace(0, 1, n + 1))
    return np.clip(np.searchsorted(edges, values, side="right") - 1, 0, n - 1), edges


def change_by_height(dnbr, before, height, unburned, bands=10):
    """Test 1: typical April change of unburned land in each height band, split by kind of land."""
    band, edges = equal_count_bins(height, unburned, bands)
    third, _ = equal_count_bins(before, unburned, 3)
    kinds = ["low score before (bare, leafless)", "middle score before", "high score before (evergreen)"]
    rows = []
    for b in range(bands):
        row = {"height band": b + 1, "height (m)": float(np.median(height[unburned & (band == b)])),
               "all unburned land": float(np.median(dnbr[unburned & (band == b)]))}
        for k, kind in enumerate(kinds):
            row[kind] = float(np.median(dnbr[unburned & (band == b) & (third == k)]))
        rows.append(row)
    return pd.DataFrame(rows)


def false_alarm_rates(flagged, height, facing, steep, unburned, bands=5):
    """Test 2: of the unburned pixels in each height band (or facing each way), what share got flagged?"""
    band, edges = equal_count_bins(height, unburned, bands)
    by_height = pd.DataFrame([{
        "height band": f"{edges[b]:.0f}-{edges[b + 1]:.0f} m",
        "false alarm rate": float(flagged[unburned & (band == b)].mean())} for b in range(bands)])
    sloped = unburned & (steep > 10)  # facing only means something on a real slope
    by_facing = pd.DataFrame([{
        "slope faces": {"N": "north", "E": "east", "S": "south", "W": "west"}[k],
        "false alarm rate": float(flagged[sloped & (facing == k)].mean())} for k in "NESW"])
    return by_height, by_facing


def lookalike_height_normal(before, height, dnbr, usable):
    """Fix C: the typical change of pixels with a similar score before the fire AND a similar height."""
    score, _ = equal_count_bins(before, usable, SCORE_GROUPS)
    band, _ = equal_count_bins(height, usable, HEIGHT_BANDS)
    group = score * HEIGHT_BANDS + band
    normal = np.full(dnbr.shape, np.nan)
    smallest = None
    for g in range(SCORE_GROUPS * HEIGHT_BANDS):
        members = usable & (group == g)
        if members.any():
            normal[members] = np.median(dnbr[members])
            smallest = members.sum() if smallest is None else min(smallest, members.sum())
    return normal, int(smallest)


def plot_checks(height, r, by_height_change, fa_height, fa_facing, path):
    """Left: height map with fix A's false alarms. Middle: test 1. Right: test 2 and the rival."""
    d = r["data"]["April"]
    band = d["after"]["nir"]
    ext = step8.extent(band)
    false_alarm = r["maps"]["April"][FIX_A] & d["usable"] & ~r["inside"]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))

    im = axes[0].imshow(height, cmap="terrain", extent=ext)
    axes[0].imshow(np.where(false_alarm, 0, np.nan), cmap="gray", vmin=0, vmax=1, extent=ext, interpolation="nearest")
    step8.draw_outline(axes[0], band, color="red")
    axes[0].set_title("Ground height, fix A's false alarms in black\n(red line = official outline)", fontsize=10)
    axes[0].set_xticks([])
    axes[0].set_yticks([])
    fig.colorbar(im, ax=axes[0], fraction=0.04, label="height (m)")

    for col, style in zip(by_height_change.columns[2:], ("k-o", "C2--s", "C1--^", "C0--v")):
        axes[1].plot(by_height_change["height (m)"], by_height_change[col], style, label=col,
                     linewidth=2.5 if col.startswith("all") else 1.2)
    axes[1].set_xlabel("ground height (m)")
    axes[1].set_ylabel("typical April change, dNBR (higher = greened up less)")
    axes[1].set_title("Test 1: unburned land only", fontsize=10)
    axes[1].legend(fontsize=8)

    labels = list(fa_height["height band"]) + [f"faces {f}" for f in fa_facing["slope faces"]]
    rates = list(fa_height["false alarm rate"]) + list(fa_facing["false alarm rate"])
    colors = ["#8c6bb1"] * len(fa_height) + ["#fdae61"] * len(fa_facing)
    axes[2].bar(range(len(rates)), rates, color=colors)
    for i, v in enumerate(rates):
        axes[2].text(i, v + 0.005, f"{v:.0%}", ha="center", fontsize=9)
    axes[2].set_xticks(range(len(rates)), labels, rotation=40, ha="right", fontsize=8)
    axes[2].set_ylabel("share of unburned pixels flagged by fix A")
    axes[2].set_title("Test 2: false-alarm rate by height (purple)\nand by the way the slope faces (orange)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    return fig


def plot_fix_c(r, scores, path):
    """April pair: fix A next to fix C, colored by outcome, plus their grades."""
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    d = r["data"]["April"]
    band, inside = d["after"]["nir"], r["inside"]
    ext = step8.extent(band)
    colors = ListedColormap(["#d7301f", "#fecc5c", "#2b8cbe"])
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), gridspec_kw={"width_ratios": [1, 1, 0.9]})
    for ax, name in zip(axes[:2], (FIX_A, FIX_C)):
        flagged = r["maps"]["April"][name] & d["usable"]
        outcome = np.full(inside.shape, np.nan)
        outcome[flagged & inside] = 0
        outcome[~flagged & inside & d["usable"]] = 1
        outcome[flagged & ~inside] = 2
        ax.imshow(np.clip(band.values / 0.4, 0, 1), cmap="gray", extent=ext)
        ax.imshow(np.where(d["usable"], np.nan, 1), cmap=ListedColormap(["white"]), extent=ext, alpha=0.6)
        ax.imshow(outcome, cmap=colors, vmin=0, vmax=2, extent=ext, interpolation="nearest")
        step8.draw_outline(ax, band)
        ax.set_title(f"April pair, {name}", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[0].legend(handles=[Patch(color="#d7301f", label="caught"), Patch(color="#fecc5c", label="missed"),
                            Patch(color="#2b8cbe", label="false alarm")], loc="lower right", fontsize=8)

    s = scores[(scores["pair"] == "April") & scores["map"].isin(["histogram", FIX_A, FIX_C])]
    x = np.arange(len(s))
    axes[2].bar(x - 0.2, s["caught"], 0.4, color="#2b8cbe", label="caught")
    axes[2].bar(x + 0.2, s["right"], 0.4, color="#fdae61", label="right")
    for xi, c, rt in zip(x, s["caught"], s["right"]):
        axes[2].text(xi - 0.2, c + 0.02, f"{c:.0%}", ha="center", fontsize=9)
        axes[2].text(xi + 0.2, rt + 0.02, f"{rt:.0%}", ha="center", fontsize=9)
    axes[2].set_xticks(x, ["plain\nhistogram", "fix A:\nlook-alikes", "fix C:\n+ height"])
    axes[2].set_ylim(0, 1.15)
    axes[2].set_title("April pair grades", fontsize=10)
    axes[2].legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    return fig


def run():
    """Everything up to the tables, so the notebook can reuse it."""
    r = step9.run()
    shape = fires.outline(step8.FIRE)
    bbox = fires.box_around(shape)
    band = r["data"]["April"]["after"]["nir"]
    height = terrain.height_like(band, bbox)
    facing, steep = terrain.slope_facing(height)
    # "Unburned" for the tests: outside the outline and more than 300 m from it (fire edges are fuzzy).
    near_edge = fires.ring_mask(shape, band, inner_m=0, outer_m=300)
    far_outside = ~r["inside"] & ~near_edge

    d = r["data"]["April"]
    unburned = d["usable"] & far_outside
    by_height_change = change_by_height(d["dnbr"], d["before"]["nbr"].values, height, unburned)
    fa_height, fa_facing = false_alarm_rates(r["maps"]["April"][FIX_A], height, facing, steep, unburned)

    smallest = {}
    for pair, pd_ in r["data"].items():
        normal, smallest[pair] = lookalike_height_normal(pd_["before"]["nbr"].values, height, pd_["dnbr"], pd_["usable"])
        with np.errstate(invalid="ignore"):
            r["maps"][pair][FIX_C] = (pd_["dnbr"] - normal) > step9.EXTRA
    rows = []
    for pair, maps in r["maps"].items():
        for name in step9.MAP_ORDER + [FIX_C]:
            rows.append({"pair": pair, "map": name, **step9.grade(maps[name], r["inside"], r["data"][pair]["usable"])})
    scores = pd.DataFrame(rows)
    return {"r": r, "height": height, "unburned": unburned, "by_height_change": by_height_change,
            "fa_height": fa_height, "fa_facing": fa_facing, "scores": scores, "smallest_group": smallest}


def main():
    hls.login()
    out = run()
    r, height = out["r"], out["height"]
    print(f"Height in the box: {np.nanmin(height):.0f} to {np.nanmax(height):.0f} m. "
          f"Typical height inside the outline {np.median(height[r['inside']]):.0f} m, "
          f"on unburned land {np.median(height[out['unburned']]):.0f} m.")

    print("\nTest 1: typical April change of UNBURNED land, by height band")
    print(out["by_height_change"].round(3).to_string(index=False))
    print("\nTest 2: fix A's false-alarm rate on unburned land")
    print(out["fa_height"].round(3).to_string(index=False))
    print(out["fa_facing"].round(3).to_string(index=False))
    print(f"\nFix C: smallest look-alike group holds {out['smallest_group']} pixels")
    print(out["scores"].to_string(index=False))

    res = ROOT / "results"
    out["by_height_change"].round(4).to_csv(res / "10_change_by_height.csv", index=False)
    pd.concat([out["fa_height"].rename(columns={"height band": "group"}),
               out["fa_facing"].rename(columns={"slope faces": "group"})]).round(4).to_csv(
        res / "10_false_alarm_rates.csv", index=False)
    out["scores"].to_csv(res / "10_burn_scores_with_fix_c.csv", index=False)

    figs = ROOT / "figures"
    plot_checks(height, r, out["by_height_change"], out["fa_height"], out["fa_facing"], figs / "10_ridge_check.png")
    plot_fix_c(r, out["scores"], figs / "10_fix_c.png")
    print("\nSaved figures/10_ridge_check.png and 10_fix_c.png")


if __name__ == "__main__":
    main()
