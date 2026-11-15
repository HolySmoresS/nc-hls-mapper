"""Step 12 (paper, Figure 1): a locator map of the three study boxes.

A locator map is a "you are here" map: it shows the reader WHERE each study area lies
before they look at any result. No new analysis here, only boxes the earlier steps used:
  - Floods: the Lumber River box (hls.STUDY_AREAS).
  - Burn scars: the box around each fire outline (fires.box_around), same as Steps 7-11.

The state outlines come from the U.S. Census Bureau (TIGERweb map service), simplified to
about 1 km detail. They are saved in data/states/ (git-ignored) and downloaded only once.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no pop-up window
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import shape

import fires
import hls

ROOT = Path(__file__).resolve().parents[1]
STATES_FILE = ROOT / "data" / "states" / "nc_and_neighbors.geojson"
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0/query"
STATES = ["NC", "VA", "TN", "SC", "GA"]  # North Carolina plus its neighbors, for context

# Colors: blue = the flood part, orange = the burn-scar part.
FLOOD, BURN = "#2166ac", "#d6604d"


def study_boxes():
    """(name, part, box) for each study area. Box = (west, south, east, north) in degrees."""
    return [
        ("Lumber River, Lumberton\n(flood, Sept 2018)", FLOOD,
         hls.STUDY_AREAS["Lumber River (Lumberton)"]),
        ("Black Cove Complex\n(mountain fire, Mar 2025)", BURN,
         fires.box_around(fires.outline("Black Cove Complex (Mar 2025)"))),
        ("Great Lakes fire\n(coastal fire, Apr 2023)", BURN,
         fires.box_around(fires.outline("Great Lakes (Apr 2023), NIFC outline"))),
    ]


def state_outlines():
    """{state code: shape}. Downloads the outlines the first time only."""
    if not STATES_FILE.exists():
        params = {
            "where": "STUSAB IN (" + ",".join(f"'{s}'" for s in STATES) + ")",
            "outFields": "NAME,STUSAB",
            "outSR": "4326",              # plain longitude / latitude
            "maxAllowableOffset": "0.01",  # simplify to about 1 km: plenty for a state map
            "f": "geojson",
        }
        with urllib.request.urlopen(TIGER + "?" + urllib.parse.urlencode(params), timeout=60) as r:
            data = json.load(r)
        STATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATES_FILE.write_text(json.dumps(data))
    data = json.loads(STATES_FILE.read_text())
    return {f["properties"]["STUSAB"]: shape(f["geometry"]) for f in data["features"]}


def draw_shape(ax, geom, **style):
    """Draw a (multi)polygon's rings as filled shapes."""
    for poly in getattr(geom, "geoms", [geom]):
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, **style)


def box_size_km(box):
    """Rough width x height of a box in km (1 degree = 91 km east-west, 111 km north-south here)."""
    return (box[2] - box[0]) * 91, (box[3] - box[1]) * 111


def plot_locator(path):
    states = state_outlines()
    boxes = study_boxes()
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for code, geom in states.items():
        if code != "NC":
            draw_shape(ax, geom, facecolor="#f0f0f0", edgecolor="#bbbbbb", linewidth=0.6)
    draw_shape(ax, states["NC"], facecolor="#fbf8ee", edgecolor="#555555", linewidth=1.0)

    # Where each label sits, as (x, y) in degrees, chosen so no label covers another.
    label_at = [(-80.2, 34.2), (-83.9, 36.2), (-76.6, 34.0)]
    for (name, color, box), (lx, ly) in zip(boxes, label_at):
        w, s, e, n = box
        ax.add_patch(Rectangle((w, s), e - w, n - s, facecolor=color, edgecolor=color,
                               alpha=0.35, linewidth=1.5))
        ax.add_patch(Rectangle((w, s), e - w, n - s, fill=False, edgecolor=color, linewidth=1.5))
        cx, cy = (w + e) / 2, (s + n) / 2
        km_w, km_h = box_size_km(box)
        ax.annotate(f"{name}\nbox {km_w:.0f} x {km_h:.0f} km", xy=(cx, cy), xytext=(lx, ly),
                    fontsize=9, color=color, ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", color=color, linewidth=0.8))

    for code, (x, y) in {"VA": (-79.0, 36.85), "TN": (-84.6, 35.85), "SC": (-81.7, 34.3),
                         "GA": (-84.3, 34.75)}.items():
        ax.text(x, y, code, fontsize=9, color="#999999", ha="center")
    ax.text(-79.3, 35.75, "North Carolina", fontsize=12, color="#555555", ha="center")

    ax.set_xlim(-85.0, -75.2)
    ax.set_ylim(33.6, 37.0)
    ax.set_aspect(111 / 91)  # so one km looks the same size in both directions at 35 N
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title("The three study areas (blue = flood, orange = burn scars)")
    fig.text(0.99, 0.01, "State outlines: U.S. Census Bureau TIGERweb", fontsize=7,
             color="#888888", ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return boxes


if __name__ == "__main__":
    out = ROOT / "figures" / "12_locator_map.png"
    for name, _, box in plot_locator(out):
        km_w, km_h = box_size_km(box)
        print(f"{name.splitlines()[0]:<26} box {tuple(round(v, 3) for v in box)}"
              f"  about {km_w:.0f} x {km_h:.0f} km")
    print("Saved", out.relative_to(ROOT))
