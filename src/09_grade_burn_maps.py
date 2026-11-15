"""Step 9 (burn scars, step 3): grade the burn maps, and try two fixes for the leaf season.

Answer key: the official fire outline. A pixel inside it counts as "really burned".
Two grades per map, the same as for the flood maps:
  - caught = share of the outline the map flagged            (recall)
  - right  = share of the map's flags that are in the outline (precision)

Step 8 showed that in the April pair the whole landscape greened up, so "no change" is not
at zero any more. Two fixes, both asking "did this pixel's score fall 0.10 MORE THAN NORMAL?":
  - Fix A, look-alikes: normal = the typical change of pixels that had a similar burn score
    before the fire, anywhere in the box. Never uses the outline.
  - Fix B, ring: normal = the typical change in a ring of land just outside the outline.
    This is what the national archive (MTBS) does. It uses the answer key to build the map.
These rules were written down before any score was computed.
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

step8 = importlib.import_module("08_burn_maps")  # reuse step 8's photo loading and its two plain maps

ROOT = Path(__file__).resolve().parents[1]
EXTRA = 0.10      # "burned" = the score fell this much more than normal (the textbook number)
GROUPS = 20       # look-alike groups, each holding the same number of pixels
KM2 = step8.KM2_PER_PIXEL
MAP_ORDER = ["textbook", "histogram", "fix A: look-alikes", "fix B: ring"]


def lookalike_normal(before_nbr, dnbr, usable, groups=GROUPS):
    """For every pixel: the typical (median) change of pixels with a similar score before the fire.

    Why it helps: bare fields, pines and leafy forest green up by different amounts in spring.
    Comparing a pixel with its own kind removes most of that.
    Why the median: about a tenth of the box burned. The median is the middle value, so a
    minority of burned pixels in a group cannot drag it far.
    """
    edges = np.quantile(before_nbr[usable], np.linspace(0, 1, groups + 1))
    group = np.clip(np.searchsorted(edges, before_nbr, side="right") - 1, 0, groups - 1)
    normal = np.full(dnbr.shape, np.nan)
    rows = []
    for g in range(groups):
        members = usable & (group == g)
        typical = np.median(dnbr[members])
        normal[members] = typical
        rows.append({"group": g + 1, "NBR before (middle)": float(np.median(before_nbr[members])),
                     "typical change": float(typical)})
    return normal, pd.DataFrame(rows)


def ring_normal(dnbr, usable, ring):
    """One number: the typical change in the unburned ring just outside the outline."""
    return float(np.median(dnbr[usable & ring]))


def build_maps(data, plain, ring):
    """All four maps for one pair of photos, plus what each fix used as "normal"."""
    before = data["before"]["nbr"].values
    dnbr, usable = data["dnbr"], data["usable"]
    normal_a, groups = lookalike_normal(before, dnbr, usable)
    normal_b = ring_normal(dnbr, usable, ring)
    with np.errstate(invalid="ignore"):  # blank pixels compare as False
        maps = {
            "textbook": plain["maps"]["textbook"],
            "histogram": plain["maps"]["histogram"],
            "fix A: look-alikes": (dnbr - normal_a) > EXTRA,
            "fix B: ring": (dnbr - normal_b) > EXTRA,
        }
    return maps, groups, normal_b


def grade(flagged, inside, usable):
    """Caught, right and F1 for one map, counting only pixels the pair could see."""
    flagged, truth = flagged & usable, inside & usable
    hits = (flagged & truth).sum()
    caught = hits / truth.sum()
    right = hits / flagged.sum() if flagged.sum() else np.nan
    f1 = 2 * caught * right / (caught + right) if hits else 0.0
    return {
        "flagged km2": round(float(flagged.sum() * KM2), 1),
        "caught": round(float(caught), 3),
        "right": round(float(right), 3),
        "F1": round(float(f1), 3),  # one number that is only high when caught AND right are both high
        "false alarms km2": round(float((flagged & ~truth).sum() * KM2), 1),
        "overall accuracy": round(float(((flagged == truth) & usable).sum() / usable.sum()), 3),
    }


def score_table(all_maps, all_data, inside):
    rows = []
    for pair, maps in all_maps.items():
        usable = all_data[pair]["usable"]
        nothing = np.zeros_like(inside)
        rows.append({"pair": pair, "map": "say nothing burned (baseline)", **grade(nothing, inside, usable)})
        for name in MAP_ORDER:
            rows.append({"pair": pair, "map": name, **grade(maps[name], inside, usable)})
    return pd.DataFrame(rows)


def plot_scores(scores, path):
    """Bars: caught and right for every map, one panel per pair."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, (pair, d) in zip(axes, scores.groupby("pair", sort=False)):
        d = d[d["map"].isin(MAP_ORDER)]
        x = np.arange(len(d))
        ax.bar(x - 0.2, d["caught"], 0.4, label="caught (share of the outline flagged)", color="#2b8cbe")
        ax.bar(x + 0.2, d["right"], 0.4, label="right (share of flags inside the outline)", color="#fdae61")
        for xi, c, r in zip(x, d["caught"], d["right"]):
            ax.text(xi - 0.2, c + 0.02, f"{c:.0%}", ha="center", fontsize=9)
            ax.text(xi + 0.2, r + 0.02, f"{r:.0%}", ha="center", fontsize=9)
        ax.set_xticks(x, [m.replace(": ", ":\n") for m in d["map"]])
        ax.set_ylim(0, 1.12)
        ax.set_title(f"{pair} pair")
    axes[0].set_ylabel("share")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=9)  # below the bars, so it hides nothing
    fig.suptitle("Burn maps graded against the official outline")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=130)
    return fig


def plot_normal(all_groups, all_ring, path):
    """What "normal change" looks like for each kind of pixel: the picture behind fix A."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for (pair, g), color in zip(all_groups.items(), ("#1b9e77", "#7570b3")):
        ax.plot(g["NBR before (middle)"], g["typical change"], "o-", color=color, label=f"{pair} pair: look-alike groups (fix A)")
        ax.axhline(all_ring[pair], color=color, linestyle="--", label=f"{pair} pair: ring outside the outline (fix B)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("burn score (NBR) before the fire: bare and leafless on the left, evergreen on the right")
    ax.set_ylabel("typical change, dNBR (below 0 = got greener)")
    ax.set_title('What counts as "normal change" for each kind of pixel')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    return fig


def plot_outcomes(all_maps, all_data, inside, path):
    """Each map colored by outcome: caught, missed, or false alarm."""
    colors = ListedColormap(["#d7301f", "#fecc5c", "#2b8cbe"])  # hit, miss, false alarm
    fig, axes = plt.subplots(2, 4, figsize=(17, 9.2))
    for row, (pair, maps) in zip(axes, all_maps.items()):
        d = all_data[pair]
        band = d["after"]["nir"]
        ext = step8.extent(band)
        for ax, name in zip(row, MAP_ORDER):
            flagged = maps[name] & d["usable"]
            outcome = np.full(inside.shape, np.nan)
            outcome[flagged & inside] = 0
            outcome[~flagged & inside & d["usable"]] = 1
            outcome[flagged & ~inside] = 2
            ax.imshow(np.clip(band.values / 0.4, 0, 1), cmap="gray", extent=ext)
            ax.imshow(np.where(d["usable"], np.nan, 1), cmap=ListedColormap(["white"]), extent=ext, alpha=0.6)
            ax.imshow(outcome, cmap=colors, vmin=0, vmax=2, extent=ext, interpolation="nearest")
            step8.draw_outline(ax, band)
            ax.set_title(f"{pair} pair, {name}", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.legend(handles=[Patch(color="#d7301f", label="caught: flagged, inside the outline"),
                        Patch(color="#fecc5c", label="missed: inside the outline, not flagged"),
                        Patch(color="#2b8cbe", label="false alarm: flagged, outside the outline"),
                        Patch(facecolor="white", edgecolor="gray", label="cloud, shadow or water (not graded)")],
               loc="lower center", ncol=4, fontsize=10)
    fig.suptitle("Every burn map, colored by outcome (black line = official outline)")
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=2.5)  # room so the row titles do not touch the row above
    fig.savefig(path, dpi=120)
    return fig


def run():
    """Everything up to the score table, so the notebook can reuse it."""
    shape = fires.outline(step8.FIRE)
    bbox = fires.box_around(shape)
    all_data = {name: step8.load_pair(bbox, pair) for name, pair in step8.PAIRS.items()}
    plain = {name: step8.make_maps(d) for name, d in all_data.items()}
    band = all_data["April"]["after"]["nir"]  # both satellites share one pixel grid
    inside = fires.outline_mask(shape, band)
    ring = fires.ring_mask(shape, band)
    all_maps, all_groups, all_ring = {}, {}, {}
    for name, d in all_data.items():
        all_maps[name], all_groups[name], all_ring[name] = build_maps(d, plain[name], ring)
    scores = score_table(all_maps, all_data, inside)
    return {"data": all_data, "maps": all_maps, "groups": all_groups, "ring_normal": all_ring,
            "inside": inside, "ring": ring, "scores": scores}


def main():
    hls.login()
    r = run()
    inside, ring = r["inside"], r["ring"]
    print(f"Outline: {inside.sum() * KM2:.1f} km2 = {inside.mean():.0%} of the box. Ring: {ring.sum() * KM2:.1f} km2.")
    for pair, d in r["data"].items():
        print(f"{pair} pair: can see {d['usable'][inside].mean():.0%} of the outline; "
              f"normal change in the ring {r['ring_normal'][pair]:+.3f}; "
              f"look-alike groups from {r['groups'][pair]['typical change'].min():+.3f} "
              f"to {r['groups'][pair]['typical change'].max():+.3f}")

    print("\nScores against the official outline")
    print(r["scores"].to_string(index=False))
    r["scores"].to_csv(ROOT / "results" / "09_burn_scores.csv", index=False)
    pd.concat([g.assign(pair=p) for p, g in r["groups"].items()]).round(3).to_csv(
        ROOT / "results" / "09_lookalike_groups.csv", index=False)

    figs = ROOT / "figures"
    plot_scores(r["scores"], figs / "09_burn_scores.png")
    plot_normal(r["groups"], r["ring_normal"], figs / "09_normal_change.png")
    plot_outcomes(r["maps"], r["data"], inside, figs / "09_burn_map_outcomes.png")
    print("\nSaved figures/09_burn_scores.png, 09_normal_change.png, 09_burn_map_outcomes.png")


if __name__ == "__main__":
    main()
