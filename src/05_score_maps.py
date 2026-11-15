"""Step 5: grade every flood map against my hand labels (the answer key).

Answer key: 269 spots labeled by eye on NOAA airplane photos (Sept 19-20, 2018) as
water / not water / can't tell (src/04_*). "Can't tell" spots are left out of the scores.

Words:
- Caught (recall): of the spots that really are water, the share the map called flood.
- Right when it says flood (precision): of the spots the map called flood, the share that really are water.
  (1 - precision = false alarms.)
- Overall accuracy: share of all spots where the map and the label agree.

Group-size correction: spots were picked as a fixed number per group (100 dark-in-NIR, 50 NIR-drop
only, 9 radar only, 110 dry), but the groups have very different sizes in the box (dry is about 95%
of it). Each spot therefore "stands for" (group pixels / labeled spots in its group) pixels, and all
scores below use those weights. Without them, dry land would count far too little.

Self-agreement: I re-labeled 40 random spots a second time without seeing my first answers.
How often the two passes agree tells us how trustworthy the answer key is.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "labels"
SEED = 0


def load(use_second_look=False):
    """One row per spot: group, my label, and what each map said there.
    use_second_look=True swaps in my second-look answer for the 40 re-labeled spots (a robustness check)."""
    if (LABELS / "labels.csv").exists():
        s = pd.read_csv(LABELS / "sample.csv")
        first = pd.read_csv(LABELS / "labels.csv").groupby("id")["label"].last()
        s["label"] = s["id"].map(first)
        second = (pd.read_csv(LABELS / "labels_recheck.csv").groupby("id")["label"].last()
                  if (LABELS / "labels_recheck.csv").exists() else pd.Series(dtype=object))
    else:  # fresh clone: use the copy of my labels saved in git
        s = pd.read_csv(ROOT / "results" / "04_labels.csv")
        s["label"] = s["label_first_pass"]
        second = s.set_index("id")["label_second_look"].dropna()
    if use_second_look:
        s["label"] = s["id"].map(second).fillna(s["label"])
    dark = rioxarray.open_rasterio(ROOT / "data" / "02_flood_dark_nir.tif").squeeze(drop=True).values
    drop = rioxarray.open_rasterio(ROOT / "data" / "02_flood_nir_drop.tif").squeeze(drop=True).values
    cmp3 = rioxarray.open_rasterio(ROOT / "data" / "03_radar_vs_nir.tif").squeeze(drop=True).values
    r, c = s["row"].values, s["col"].values
    s["dark-in-NIR"] = dark[r, c] == 2
    s["NIR-drop"] = drop[r, c] == 2
    s["radar"] = np.isin(cmp3[r, c], (2, 3))
    s["both NIR rules"] = s["dark-in-NIR"] & s["NIR-drop"]
    s["say dry everywhere"] = False  # baseline: a "map" with no flood at all
    # Sanity check: each spot's group must match what the maps say (catches row/col mix-ups).
    expect = {"dark_nir": s["dark-in-NIR"], "drop_only": ~s["dark-in-NIR"] & s["NIR-drop"],
              "radar_only": ~s["dark-in-NIR"] & ~s["NIR-drop"] & s["radar"],
              "dry": ~s["dark-in-NIR"] & ~s["NIR-drop"] & ~s["radar"]}
    for g, ok in expect.items():
        assert ok[s["group"] == g].all(), f"group {g} does not match the maps"
    return s


def weights(s):
    """How many box pixels each labeled spot stands for (group pixels / labeled spots in group)."""
    n = s.groupby("group")["id"].transform("count")
    return s["group_pixels"] / n


def scores(s, w, col):
    """Weighted recall, precision, accuracy for one map. s must contain only water/not_water."""
    truth = (s["label"] == "water").values
    pred = s[col].values
    tp = w[pred & truth].sum()
    fp = w[pred & ~truth].sum()
    fn = w[~pred & truth].sum()
    tn = w[~pred & ~truth].sum()
    return {
        "map": col,
        "caught (recall)": tp / (tp + fn),
        "right when it says flood (precision)": tp / (tp + fp) if tp + fp > 0 else np.nan,
        "overall accuracy": (tp + tn) / (tp + fp + fn + tn),
        "flood km2 by map": (tp + fp) * 0.0009,
        "estimated real flood km2": (tp + fn) * 0.0009,
    }


def bootstrap(s, w, col, n=2000):
    """Uncertainty: re-draw the spots at random within each group many times and re-score.
    The middle 95% of results is the range we report (like asking 'how much could luck move this?')."""
    rng = np.random.default_rng(SEED)
    out = []
    groups = [s.index[s["group"] == g].values for g in s["group"].unique()]
    for _ in range(n):
        idx = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])
        ss, ww = s.loc[idx].reset_index(drop=True), w.loc[idx].reset_index(drop=True)
        r = scores(ss, ww.values, col)
        out.append([r["caught (recall)"], r["right when it says flood (precision)"]])
    lo, hi = np.nanpercentile(np.array(out), [2.5, 97.5], axis=0)
    return lo, hi


def plot_scores(table, ranges, path):
    """Bars: share of real flood caught, and share right when it says flood, with 95% ranges."""
    maps = [m for m in table["map"] if m in ranges]
    t = table.set_index("map").loc[maps]
    x = np.arange(len(maps))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for k, (col, lo_i, hi_i, color, label) in enumerate((
            ("caught (recall)", 0, 1, "#2b83ba", "caught: share of real flood found"),
            ("right when it says flood (precision)", 2, 3, "#fdae61", "right when it says flood"))):
        vals = t[col].fillna(0).values
        lo = np.array([ranges[m][lo_i] for m in maps])
        hi = np.array([ranges[m][hi_i] for m in maps])
        err = np.vstack([np.clip(vals - lo, 0, None), np.clip(hi - vals, 0, None)])
        ax.bar(x + (k - 0.5) * 0.38, vals, 0.38, yerr=err, capsize=4, color=color, label=label)
    ax.set_xticks(x, maps)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("share (0 to 1)")
    ax.set_title("How good is each flood map? (black lines = 95% range from re-drawing the spots)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def self_agreement(s):
    path = LABELS / "labels_recheck.csv"
    if path.exists():
        second = pd.read_csv(path).groupby("id")["label"].last()
    elif (ROOT / "results" / "04_labels.csv").exists():
        second = pd.read_csv(ROOT / "results" / "04_labels.csv").set_index("id")["label_second_look"].dropna()
    else:
        print("\n(No second-look labels: self-agreement skipped.)")
        return None
    both = s.set_index("id")["label"].reindex(second.index)
    tab = pd.crosstab(both.rename("first pass"), second.rename("second look"))
    agree = (both == second).mean()
    sure = (both != "cant_tell") & (second != "cant_tell")
    agree_sure = (both[sure] == second[sure]).mean()
    print(f"\nSelf-agreement on {len(second)} re-labeled spots: {agree:.0%} same answer "
          f"({agree_sure:.0%} when neither pass said can't tell)")
    print(tab)
    return {"spots": len(second), "agree": agree, "agree_without_cant_tell": agree_sure}


def main():
    s = load()
    print("Labels by group:")
    print(pd.crosstab(s["group"], s["label"]))
    s = s[s["label"].isin(["water", "not_water"])].reset_index(drop=True)
    print(f"\nScoring on {len(s)} spots (can't-tell left out)")
    w = weights(s)
    rows = []
    ranges = {}
    for col in ("say dry everywhere", "dark-in-NIR", "NIR-drop", "both NIR rules", "radar"):
        r = scores(s, w.values, col)
        if col != "say dry everywhere":
            (rlo, plo), (rhi, phi) = bootstrap(s, w, col)
            ranges[col] = (rlo, rhi, plo, phi)
            r["recall 95% range"] = f"{rlo:.0%}-{rhi:.0%}"
            r["precision 95% range"] = f"{plo:.0%}-{phi:.0%}"
        rows.append(r)
    table = pd.DataFrame(rows)
    plot_scores(table, ranges, ROOT / "figures" / "05_map_scores.png")
    pd.set_option("display.width", 200)
    print(table.round(3).to_string(index=False))

    # Unweighted look, per group: what share of each group's spots really were water?
    per_group = s.groupby("group")["label"].apply(lambda x: (x == "water").mean()).rename("share water")
    print("\nShare of spots labeled water, by group (no weights):")
    print(per_group.round(2))

    out = ROOT / "results"
    table.to_csv(out / "05_map_scores.csv", index=False)
    per_group.to_csv(out / "05_share_water_by_group.csv")
    agree = self_agreement(load())
    if agree:
        pd.DataFrame([agree]).to_csv(out / "05_self_agreement.csv", index=False)
        # Robustness: how much do the grades move if the second-look answers replace the first?
        s2 = load(use_second_look=True)
        s2 = s2[s2["label"].isin(["water", "not_water"])].reset_index(drop=True)
        w2 = weights(s2)
        alt = pd.DataFrame([scores(s2, w2.values, c) for c in ("dark-in-NIR", "NIR-drop", "both NIR rules", "radar")])
        print("\nSame scores with the 40 second-look answers swapped in:")
        print(alt.round(3).to_string(index=False))
        alt.to_csv(out / "05_map_scores_second_look.csv", index=False)
    print("\nSaved results/05_*.csv")


if __name__ == "__main__":
    main()
