"""Step 1: which river has clear photos before AND after Hurricane Florence?

For each study box we:
  1. ask NASA for every HLS photo from mid-August to early October 2018,
  2. read only that photo's cloud mask (Fmask) inside our box,
  3. measure how much of the WHOLE box is clear (seen by the satellite, no cloud, no shadow).
Then we draw a timeline so we can pick the river with the best photos.
Result (Nov 14, 2026): only the Lumber River box had a clear photo soon after the storm
(Sept 18, 86% clear), so it became our study area.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import hls

ROOT = Path(__file__).resolve().parents[1]
START, END = "2018-08-15", "2018-10-10"
CLEAR_ENOUGH = 0.8  # a photo "counts" if at least 80% of the box is clear


def measure_area(name, bbox, verbose=True):
    """One row per photo: date, satellite, tile, NASA's tile cloud %, and our box-clear share."""
    rows = []
    for g in hls.search(bbox, START, END):
        info = hls.describe(g)
        try:
            fmask = hls.read_band(hls.band_url(g, "Fmask"), bbox)
            info["clear"], info["seen"] = hls.clear_fraction(fmask, bbox)
        except Exception as err:  # one bad file should not stop the whole count
            print(f"  could not read {info['name']}: {err}")
            info["clear"], info["seen"] = np.nan, np.nan
        info["area"] = name
        rows.append(info)
        if verbose:
            print(f"  {info['date']}  {info['satellite']:<10} {info['tile']}  "
                  f"tile cloud {info['tile_cloud_pct']:>4.0f}%  box clear {info['clear']:.0%}")
    df = pd.DataFrame(rows)
    # The box can touch several tiles, so one pass of the satellite can show up more than once.
    # Keep the copy that sees the most clear ground in the whole box.
    df = df.sort_values("clear", ascending=False).drop_duplicates(["date", "satellite"])
    return df.sort_values("date")


def summarize(df):
    """How many good photos before and after landfall, and how soon after?"""
    landfall = pd.Timestamp(hls.LANDFALL)
    rows = []
    for name, d in df.groupby("area", sort=False):
        good = d[d["clear"] >= CLEAR_ENOUGH]
        before = good[good["date"] < landfall]
        after = good[good["date"] > landfall]
        first_after = after["date"].min()
        rows.append({
            "river": name,
            "photos": len(d),
            "good before": len(before),
            "good after": len(after),
            "first good after": first_after.date() if pd.notna(first_after) else "none",
            "days after landfall": (first_after - landfall).days if pd.notna(first_after) else None,
        })
    return pd.DataFrame(rows)


def plot_timeline(df, path):
    """One row per river, one dot per photo, color = share of box clear."""
    landfall = pd.Timestamp(hls.LANDFALL)
    fig, ax = plt.subplots(figsize=(10, 3.6))
    names = list(hls.STUDY_AREAS)
    for i, name in enumerate(names):
        d = df[df["area"] == name]
        for sat, marker in (("Landsat", "s"), ("Sentinel-2", "o")):
            dd = d[d["satellite"] == sat]
            sc = ax.scatter(dd["date"], np.full(len(dd), i), c=dd["clear"], cmap="viridis",
                            vmin=0, vmax=1, s=np.where(dd["clear"] >= CLEAR_ENOUGH, 140, 45),
                            marker=marker, edgecolor="black", linewidth=0.5)
    ax.axvline(landfall, color="crimson", linestyle="--")
    ax.text(landfall, len(names) - 0.45, " Florence landfall", color="crimson", va="bottom")
    ax.set_yticks(range(len(names)), names)
    ax.set_ylim(-0.6, len(names) - 0.1)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))  # "Sep 17" instead of long dates
    ax.set_title("HLS photos over each river box\n(big dot = at least 80% clear; square = Landsat, circle = Sentinel-2)")
    fig.colorbar(sc, ax=ax, label="share of box clear")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def main():
    hls.login()
    tables = []
    for name, bbox in hls.STUDY_AREAS.items():
        print(name)
        tables.append(measure_area(name, bbox))
    df = pd.concat(tables, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "01_clear_photos.csv", index=False)

    summary = summarize(df)
    print("\nSummary (a photo counts if at least 80% of the box is clear)")
    print(summary.to_string(index=False))
    summary.to_csv(out / "01_summary.csv", index=False)

    fig_path = ROOT / "figures" / "01_clear_photos_timeline.png"
    plot_timeline(df, fig_path)
    print(f"\nSaved {fig_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
