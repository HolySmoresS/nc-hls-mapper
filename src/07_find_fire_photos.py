"""Step 7 (burn scars, step 1): which fire has clear photos before AND after it burned?

Same idea as step 1 for the floods. For each of three candidate fires we:
  1. fetch the official outline and draw a box around it with a 3 km margin (src/fires.py),
  2. ask NASA for every HLS photo from 60 days before the fire to 90 days after,
  3. read only each photo's cloud mask (Fmask) inside the box,
  4. measure how much of the WHOLE box is clear.
Then we draw the outlines and a timeline, so the fire is chosen by data, not by a hunch.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import fires
import hls

ROOT = Path(__file__).resolve().parents[1]
DAYS_BEFORE, DAYS_AFTER = 60, 90
CLEAR_ENOUGH = 0.8  # same rule as the flood phase: a photo "counts" if 80% of the box is clear


def measure_fire(name, bbox, start, verbose=True):
    """One row per photo: date, satellite, tile, and the share of the whole box that is clear."""
    day0 = pd.Timestamp(start)
    first = (day0 - pd.Timedelta(days=DAYS_BEFORE)).strftime("%Y-%m-%d")
    last = (day0 + pd.Timedelta(days=DAYS_AFTER)).strftime("%Y-%m-%d")
    rows = []
    for g in hls.search(bbox, first, last):
        info = hls.describe(g)
        try:
            fmask = hls.read_band(hls.band_url(g, "Fmask"), bbox)
            info["clear"], info["seen"] = hls.clear_fraction(fmask, bbox)
        except Exception as err:  # one bad file should not stop the whole count
            print(f"  could not read {info['name']}: {err}")
            info["clear"], info["seen"] = np.nan, np.nan
        info["fire"] = name
        rows.append(info)
        if verbose:
            print(f"  {info['date']}  {info['satellite']:<10} {info['tile']}  "
                  f"seen {info['seen']:.0%}  box clear {info['clear']:.0%}", flush=True)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    # A box can touch two tiles, so one pass can show up twice. Keep the copy that sees the most.
    df = df.sort_values("clear", ascending=False).drop_duplicates(["date", "satellite"]).sort_values("date")
    # Days counted from the day the fire started, so fires from different years line up.
    df["day"] = (df["date"] - day0).dt.days
    return df


def summarize(df):
    """Per fire: how many good photos before and after, and how close to the fire they are."""
    rows = []
    for name, d in df.groupby("fire", sort=False):
        good = d[d["clear"] >= CLEAR_ENOUGH]
        before, after = good[good["day"] < 0], good[good["day"] > 0]
        rows.append({
            "fire": name,
            "photos": len(d),
            "good before": len(before),
            "last good before (days)": int(before["day"].max()) if len(before) else None,
            "good after": len(after),
            "first good after (days)": int(after["day"].min()) if len(after) else None,
            "tiles": " ".join(sorted(d["tile"].unique())),
        })
    return pd.DataFrame(rows)


def plot_outlines(path):
    """The three official outlines inside their boxes, all drawn at the same scale."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4))
    for ax, name in zip(axes, fires.FIRES):
        shape = fires.outline(name)
        w, s, e, n = fires.box_around(shape)
        lon0, lat0 = (w + e) / 2, (s + n) / 2
        # Turn degrees into km from the box centre, so 1 km looks the same in every panel.
        for piece in getattr(shape, "geoms", [shape]):
            x, y = piece.exterior.xy
            ax.fill((np.array(x) - lon0) * 91, (np.array(y) - lat0) * 111, color="#d95f02", alpha=0.7)
        bx, by = (e - w) * 91 / 2, (n - s) * 111 / 2
        ax.plot([-bx, bx, bx, -bx, -bx], [-by, -by, by, by, -by], color="black", linewidth=1)
        ax.set_xlim(-16, 16)
        ax.set_ylim(-16, 16)
        ax.set_aspect("equal")
        ax.set_title(f"{name}\n{fires.area_km2(shape):.0f} km$^2$ burned (official outline)", fontsize=10)
        ax.set_xlabel("km")
    axes[0].set_ylabel("km")
    fig.suptitle("Official fire outlines (orange) inside our study boxes (black), same scale")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def plot_timeline(df, path):
    """One row per fire, one dot per photo, placed by days from the fire's start."""
    names = list(fires.FIRES)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for i, name in enumerate(names):
        d = df[df["fire"] == name]
        for sat, marker in (("Landsat", "s"), ("Sentinel-2", "o")):
            dd = d[d["satellite"] == sat]
            sc = ax.scatter(dd["day"], np.full(len(dd), i), c=dd["clear"], cmap="viridis", vmin=0, vmax=1,
                            s=np.where(dd["clear"] >= CLEAR_ENOUGH, 140, 45), marker=marker,
                            edgecolor="black", linewidth=0.5)
    ax.axvline(0, color="crimson", linestyle="--")
    ax.text(0, len(names) - 0.45, " fire starts", color="crimson", va="bottom")
    ax.set_yticks(range(len(names)), names)
    ax.set_ylim(-0.6, len(names) - 0.1)
    ax.set_xlabel("days before (-) and after (+) the fire started")
    ax.set_title("HLS photos over each fire box\n(big dot = at least 80% clear; square = Landsat, circle = Sentinel-2)")
    fig.colorbar(sc, ax=ax, label="share of box clear")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def false_color(granule, bbox, satellite):
    """A picture where burns stand out: shortwave infrared shown as red, near-infrared as green.

    Healthy plants look green. Burned ground looks red-brown, because it reflects
    more shortwave infrared and less near-infrared.
    """
    b = hls.read_reflectance(granule, bbox, satellite, names=("swir2", "nir", "red"))
    # Each band is stretched by a different amount so none of them washes out the others.
    rgb = np.dstack([b["swir2"].values / 0.30, b["nir"].values / 0.40, b["red"].values / 0.20])
    return np.clip(np.nan_to_num(rgb), 0, 1), b["nir"]


def plot_first_look(name, before, after, satellite, path):
    """Before and after in false color, with the official outline drawn on top."""
    from pyproj import Transformer

    shape = fires.outline(name)
    bbox = fires.box_around(shape)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, date, label in zip(axes, (before, after), ("before", "after")):
        g = hls.find_photo(bbox, date, satellite)
        rgb, nir = false_color(g, bbox, satellite)
        x, y = nir.x.values, nir.y.values
        ax.imshow(rgb, extent=(x.min(), x.max(), y.min(), y.max()))
        # The outline is in longitude/latitude; the photo uses a metre grid. Convert to match.
        t = Transformer.from_crs("EPSG:4326", nir.rio.crs, always_xy=True)
        for piece in getattr(shape, "geoms", [shape]):
            px, py = t.transform(*piece.exterior.xy)
            ax.plot(px, py, color="white", linewidth=1.2)
        ax.set_title(f"{label}: {date} ({satellite})")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(f"{name}: false color (burns look red-brown), official outline in white")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def main():
    hls.login()
    (ROOT / "figures").mkdir(exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)

    plot_outlines(ROOT / "figures" / "07_fire_outlines.png")
    print("Saved figures/07_fire_outlines.png")

    tables = []
    for name, fire in fires.FIRES.items():
        shape = fires.outline(name)
        bbox = fires.box_around(shape)
        print(f"\n{name}: outline {fires.area_km2(shape):.1f} km2, box {bbox}")
        tables.append(measure_fire(name, bbox, fire["start"]))
    df = pd.concat(tables, ignore_index=True)
    df.to_csv(ROOT / "results" / "07_fire_photos.csv", index=False)

    summary = summarize(df)
    print("\nSummary (a photo counts if at least 80% of the box is clear)")
    print(summary.to_string(index=False))
    summary.to_csv(ROOT / "results" / "07_fire_summary.csv", index=False)

    plot_timeline(df, ROOT / "figures" / "07_fire_photos_timeline.png")
    print("Saved figures/07_fire_photos_timeline.png")

    # First look at the fire with the best photos: is the scar visible at all?
    # Both photos are Landsat and 100% clear. March 26 is while the fire was still growing.
    plot_first_look("Black Cove Complex (Mar 2025)", "2025-03-18", "2025-03-26", "Landsat",
                    ROOT / "figures" / "07_black_cove_first_look.png")
    print("Saved figures/07_black_cove_first_look.png")


if __name__ == "__main__":
    main()
