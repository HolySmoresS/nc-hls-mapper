"""Burn-scar phase helpers: the candidate fires, their official outlines, and a box around each.

An "outline" (fire crews call it a perimeter) is the official line drawn around a fire.
It is our answer key later, so we fetch it from the agencies, never draw it ourselves.
  - NIFC = National Interagency Fire Center: outlines shared by the fire agencies.
  - MTBS = Monitoring Trends in Burn Severity: a national archive of larger fires.
Outlines are saved in data/fires/ (git-ignored) and can always be downloaded again.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import shapely
from pyproj import Geod, Transformer
from rasterio.features import geometry_mask
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUTLINE_DIR = ROOT / "data" / "fires"

NIFC = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Interagency_Perimeters/FeatureServer/0"
MTBS = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MTBS_01/MapServer/"  # + one layer number per year

# The three candidates (checked Nov 15, 2026: each one has an official outline).
# "start" is the day the fire was first reported, taken from the same official record.
# "near" is a rough search area (west, south, east, north) so a fire with the same name
# somewhere else in the country can never be picked up by mistake.
FIRES = {
    "Black Cove Complex (Mar 2025)": {
        "key": "black_cove",
        "source": "NIFC",
        "url": NIFC,
        # A "complex" is several fires managed as one. This one has three pieces.
        "where": "poly_IncidentName IN ('Black Cove', 'Deep Woods', 'Fish Hook')",
        "near": (-82.50, 35.10, -82.10, 35.40),
        "start": "2025-03-19",
    },
    "Tellico (Nov 2016)": {
        "key": "tellico",
        "source": "MTBS",
        "url": MTBS + "67",  # layer 67 = fires of 2016
        "where": "fire_id = 'NC3527408356020161103'",
        "near": (-84.0, 35.0, -83.2, 35.6),
        "start": "2016-11-03",  # MTBS date. Other sources say Oct 23; our window covers both.
    },
    "Great Lakes (Apr 2023)": {
        "key": "great_lakes",
        "source": "MTBS",
        "url": MTBS + "80",  # layer 80 = fires of 2023
        "where": "fire_id = 'NC3486007705120230419'",
        "near": (-77.5, 34.6, -76.7, 35.2),
        "start": "2023-04-19",
    },
}

MARGIN_KM = 3  # extra room around the outline, so the box also holds forest that did NOT burn
ACRES_PER_KM2 = 247.105


def download_outline(fire):
    """Ask the agency's map service for the outline as GeoJSON (a plain-text map format)."""
    params = {
        "where": fire["where"],
        "geometry": ",".join(str(v) for v in fire["near"]),
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "outSR": 4326,  # plain longitude / latitude
        "f": "geojson",
    }
    with urllib.request.urlopen(fire["url"] + "/query?" + urllib.parse.urlencode(params), timeout=120) as r:
        data = json.load(r)
    if not data.get("features"):
        raise LookupError(f"no outline found for {fire['key']}: {str(data)[:200]}")
    return data


def outline(name):
    """The fire's outline as one shape (pieces joined). Downloads it the first time only."""
    fire = FIRES[name]
    path = OUTLINE_DIR / f"{fire['key']}.geojson"
    if not path.exists():
        OUTLINE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(download_outline(fire)))
    data = json.loads(path.read_text())
    return unary_union([shape(f["geometry"]) for f in data["features"]])


def area_km2(geom):
    """True ground area of a longitude/latitude shape, measured on the curved Earth."""
    return abs(Geod(ellps="WGS84").geometry_area_perimeter(geom)[0]) / 1e6


def box_around(geom, margin_km=MARGIN_KM):
    """(west, south, east, north) box around a shape plus a margin.

    One degree of latitude is about 111 km everywhere. One degree of longitude shrinks
    toward the poles; at North Carolina's latitude (about 35 N) it is about 91 km.
    """
    west, south, east, north = geom.bounds
    dlat = margin_km / 111.0
    dlon = margin_km / 91.0
    return (round(west - dlon, 3), round(south - dlat, 3), round(east + dlon, 3), round(north + dlat, 3))



def outline_mask(geom, band):
    """True for every pixel of a photo band that lies inside the outline.

    The outline is in longitude/latitude; the photo uses a metre grid, so the outline is converted first.
    """
    t = Transformer.from_crs("EPSG:4326", band.rio.crs, always_xy=True)
    moved = shapely.transform(geom, lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1])))
    return geometry_mask([moved], out_shape=band.shape, transform=band.rio.transform(), invert=True)


def triangle_cutoff(values, width=0.01, tail_pct=99.9):
    """A cutoff picked from the histogram alone (the "triangle method", Zack and others, 1977).

    Most pixels did not burn, so the histogram is one big pile with a long tail on the right
    (the burn). Stretch a string from the top of the pile to the end of the tail. The cutoff
    is where the histogram sags furthest below the string: the foot of the pile.
    Returns (cutoff, peak of the pile). It never needs the fire outline.
    """
    edges = np.arange(-1, 1 + width, width)
    counts, _ = np.histogram(values, bins=edges)
    middles = edges[:-1] + width / 2
    peak = counts.argmax()
    end = np.searchsorted(middles, np.percentile(values, tail_pct))
    x = np.arange(peak, end + 1)
    y = counts[peak:end + 1].astype(float)
    # Rescale both directions to 0..1 so "distance below the string" is fair.
    xs = (x - x[0]) / (x[-1] - x[0])
    ys = y / y[0]
    string = 1 + (ys[-1] - 1) * xs
    return float(middles[x[(string - ys).argmax()]]), float(middles[peak])


if __name__ == "__main__":
    # Quick check: download each outline and compare its size with the official acres.
    for name in FIRES:
        g = outline(name)
        box = box_around(g)
        km2 = area_km2(g)
        box_km2 = (box[2] - box[0]) * 91 * (box[3] - box[1]) * 111
        print(f"{name:<32} outline {km2:6.1f} km2 = {km2 * ACRES_PER_KM2:7,.0f} acres;"
              f" box {box} about {box_km2:4.0f} km2; burned share of box {km2 / box_km2:.0%}")
