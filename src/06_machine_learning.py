"""Step 6 (Week 4): can machine learning beat the near-infrared rule?

Data: my 255 labeled spots (water / not water; can't-tell left out), 21 clues per spot (src/features.py).
Models:
- Logistic regression: one straight dividing line through the clues (like Project 0's linear regression,
  but for yes/no answers).
- Random forest: 300 small decision trees, each sees a random part of the data; they vote.
Baseline: the dark-in-NIR rule from step 2 (NIR < 0.10 after, not before). It needs no training.

Fair testing = practice exams by AREA (spatial cross-validation):
- The box is cut into 4 x 4 = 16 blocks. Each practice exam hides whole blocks, trains on the rest,
  and grades on the hidden blocks. Every spot is graded once, by a model that never saw its block.
- Why blocks, not single spots: neighbouring spots look almost the same (same field, same flood),
  so hiding single spots would let the model "peek" through a neighbour. Same lesson as Project 0,
  where we split by engine, not by row.
- For comparison we also run ordinary random practice exams (spots shuffled) to see if they look
  too good.
Grades use the same group-size weights and bootstrap ranges as step 5.
"""
import importlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import features

ROOT = Path(__file__).resolve().parents[1]
step5 = importlib.import_module("05_score_maps")  # reuse load(), weights(), scores(), bootstrap()
BLOCKS = 4          # 4 x 4 blocks
FOLDS = 5
SEED = 0


def models():
    return {
        "logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=SEED, n_jobs=-1),
    }


def spot_table():
    """Labeled spots (water / not water) with their 21 clues and their area block."""
    s = step5.load()
    s = s[s["label"].isin(["water", "not_water"])].reset_index(drop=True)
    f = features.load()
    names = list(f)
    X = np.column_stack([f[k][s["row"], s["col"]] for k in names])
    assert np.isfinite(X).all(), "a labeled spot has a missing clue"
    shape = next(iter(f.values())).shape
    s["block"] = (s["row"] * BLOCKS // shape[0]) * BLOCKS + (s["col"] * BLOCKS // shape[1])
    y = (s["label"] == "water").values
    return s, X, y, names


def out_of_fold(X, y, splits):
    """Each spot's prediction comes from a model trained WITHOUT that spot's fold."""
    preds = {name: np.zeros(len(y), bool) for name in models()}
    for train, test in splits:
        for name, m in models().items():
            m.fit(X[train], y[train])
            preds[name][test] = m.predict(X[test]).astype(bool)
    return preds


def grade(s, preds, cols_extra=("dark-in-NIR",)):
    w = step5.weights(s)
    s = s.copy()
    rows = []
    for name, p in preds.items():
        s[name] = p
    for col in list(cols_extra) + list(preds):
        r = step5.scores(s, w.values, col)
        (rlo, plo), (rhi, phi) = step5.bootstrap(s, w, col)
        r["recall 95% range"] = f"{rlo:.0%}-{rhi:.0%}"
        r["precision 95% range"] = f"{plo:.0%}-{phi:.0%}"
        r["F1"] = 2 * r["caught (recall)"] * r["right when it says flood (precision)"] / (
            r["caught (recall)"] + r["right when it says flood (precision)"])
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    s, X, y, names = spot_table()
    print(f"{len(y)} labeled spots, {y.sum()} water; {len(names)} clues; "
          f"{s['block'].nunique()} of {BLOCKS * BLOCKS} blocks contain spots")

    # --- Fair: practice exams by area block ---
    spatial = list(GroupKFold(n_splits=FOLDS).split(X, y, groups=s["block"]))
    for k, (_, test) in enumerate(spatial):
        print(f"  area exam {k + 1}: {len(test)} spots, {y[test].sum()} water, blocks {sorted(s['block'][test].unique())}")
    fair = grade(s, out_of_fold(X, y, spatial))
    pd.set_option("display.width", 220)
    print("\nPractice exams by AREA (fair):")
    print(fair.round(3).to_string(index=False))

    # --- For comparison: ordinary random practice exams (neighbours can leak) ---
    rand = list(StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED).split(X, y))
    shuffled = grade(s, out_of_fold(X, y, rand))
    print("\nOrdinary RANDOM practice exams (can look too good):")
    print(shuffled.round(3).to_string(index=False))

    out = ROOT / "results"
    fair.to_csv(out / "06_scores_by_area.csv", index=False)
    shuffled.to_csv(out / "06_scores_random.csv", index=False)

    # --- Which clues does the forest lean on? (trained on all labeled spots) ---
    rf = models()["random forest"].fit(X, y)
    imp = pd.Series(rf.feature_importances_, index=names).sort_values(ascending=False)
    print("\nRandom forest: most-used clues")
    print(imp.head(8).round(3).to_string())
    imp.to_csv(out / "06_clue_importance.csv", header=["importance"])

    figs = ROOT / "figures"
    # Picture 1: grades, fair vs random exams
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for a, (title, t) in zip(ax, (("Practice exams by area (fair)", fair), ("Random practice exams", shuffled))):
        x = np.arange(len(t))
        a.bar(x - 0.2, t["caught (recall)"], 0.4, color="#2b83ba", label="caught (recall)")
        a.bar(x + 0.2, t["right when it says flood (precision)"], 0.4, color="#fdae61", label="right when it says flood (precision)")
        a.set_xticks(x, t["map"]); a.set_title(title); a.set_ylim(0, 1)
    ax[0].set_ylabel("share (0 to 1)")
    ax[0].legend(loc="upper center", bbox_to_anchor=(1.05, -0.12), ncol=2, frameon=False)
    fig.tight_layout(); fig.savefig(figs / "06_ml_vs_rule.png", dpi=130, bbox_inches="tight")

    # Picture 2: clue importance
    fig, ax = plt.subplots(figsize=(7, 5))
    imp.head(12)[::-1].plot.barh(ax=ax, color="gray")
    ax.set_title("Random forest: which clues it uses most"); ax.set_xlabel("importance (share of all splits' benefit)")
    fig.tight_layout(); fig.savefig(figs / "06_clue_importance.png", dpi=130)

    # Picture 3: random-forest flood map for the whole box (trained on all labeled spots)
    f = features.load()
    grid = features.template()
    cats_in = grid.values
    ok = (cats_in != 3) & np.all([np.isfinite(f[k]) for k in names], axis=0)
    Xall = np.column_stack([f[k][ok] for k in names])
    water = np.zeros(cats_in.shape, bool)
    water[ok] = rf.predict(Xall).astype(bool)
    flood = water & (cats_in != 1) & ok   # new water: not water before (step 2's before-water)
    cats = np.zeros(cats_in.shape, np.uint8)
    cats[cats_in == 1] = 1
    cats[flood] = 2
    cats[~ok] = 3
    colors = ["#f0f0f0", "#2b83ba", "#d7191c", "#9e9e9e"]
    fig, ax = plt.subplots(1, 2, figsize=(16, 6.4))
    for a, (title, c) in zip(ax, ((f"Dark-in-NIR rule: {(cats_in == 2).sum() * 0.0009:.1f} km² flood", cats_in),
                                  (f"Random forest: {flood.sum() * 0.0009:.1f} km² flood", cats))):
        a.imshow(c, cmap=ListedColormap(colors), vmin=-0.5, vmax=3.5, interpolation="nearest")
        a.set_title(title); a.set_xticks([]); a.set_yticks([])
    fig.legend(handles=[Patch(color=c, label=l) for c, l in zip(colors, [
        "dry land", "water before", "new flood water", "cloud or no data"])], loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95)); fig.savefig(figs / "06_rf_flood_map.png", dpi=120)
    grid.copy(data=cats).rio.to_raster(ROOT / "data" / "06_flood_random_forest.tif")
    print(f"\nRandom-forest flood map: {flood.sum() * 0.0009:.1f} km2 (rule: {(cats_in == 2).sum() * 0.0009:.1f} km2)")
    print("Saved figures/06_*.png, results/06_*.csv, data/06_flood_random_forest.tif")


if __name__ == "__main__":
    main()
