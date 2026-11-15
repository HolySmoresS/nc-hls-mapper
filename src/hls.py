"""Shared helpers for the NC flood mapper: login, search, and reading small pieces of HLS images.

Every script and notebook imports from here, so the same rules are used everywhere.
"""
import os
import tempfile

import earthaccess
import numpy as np
import rasterio
from pyproj import Transformer
import rioxarray  # noqa: F401  (adds the .rio tools to xarray)

# Hurricane Florence came ashore in NC on this day. Photos before it are "before", after it are "after".
LANDFALL = "2018-09-14"

# Rough first-guess boxes around three flooded river towns: (west, south, east, north) in degrees.
# They are small (about 20-30 km across) so we only read the part of each image we need.
STUDY_AREAS = {
    "Lumber River (Lumberton)": (-79.15, 34.55, -78.90, 34.70),
    "Neuse River (Kinston)": (-77.75, 35.18, -77.45, 35.35),
    "Cape Fear River (Fayetteville)": (-78.95, 34.95, -78.75, 35.15),
}

# Chosen study area (Nov 14, 2026): the only box with a clear photo soon after the storm
# (Sept 18, 2018: 86% of the box clear). See src/01_find_clear_photos.py.
STUDY_AREA = "Lumber River (Lumberton)"

# Fmask is one number per pixel; each "bit" of that number is a yes/no flag.
# HLS v2: bit 1 = cloud, bit 2 = next to cloud or shadow, bit 3 = cloud shadow. 255 = no data.
FMASK_CLOUD_BITS = (1 << 1) | (1 << 2) | (1 << 3)
FMASK_NODATA = 255


def login():
    """Sign in with the login saved in ~/.netrc. Never asks for or prints the password."""
    auth = earthaccess.login(strategy="netrc")
    if not auth.authenticated:
        raise RuntimeError("Earthdata login failed. Run the one-time interactive login again.")
    return auth


def search(bbox, start, end):
    """Find every HLS photo (Landsat L30 and Sentinel-2 S30) touching the box between two dates."""
    return earthaccess.search_data(
        short_name=["HLSL30", "HLSS30"], version="2.0", bounding_box=bbox, temporal=(start, end)
    )


def gdal_env():
    """Settings so GDAL can read NASA's cloud files with the saved login.

    The cookie file holds a temporary session ticket, so it lives in the system temp folder,
    never inside this repo.
    """
    cookies = os.path.join(tempfile.gettempdir(), "earthdata_cookies.txt")
    return rasterio.Env(
        GDAL_HTTP_COOKIEFILE=cookies,
        GDAL_HTTP_COOKIEJAR=cookies,
        GDAL_HTTP_NETRC="YES",
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",  # don't list the whole folder, just open the file
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS="TIF",
        GDAL_HTTP_MAX_RETRY="5",
        GDAL_HTTP_RETRY_DELAY="2",
    )


def band_url(granule, band):
    """Web address of one band (for example 'Fmask' or 'B03') inside one HLS photo."""
    for link in granule.data_links():
        if link.endswith(f".{band}.tif"):
            return link
    raise KeyError(f"band {band} not found in {granule['umm']['GranuleUR']}")


def read_band(url, bbox):
    """Read only the pixels inside the box (much faster than downloading the whole tile)."""
    with gdal_env():
        da = rioxarray.open_rasterio(url, masked=False).squeeze("band", drop=True)
        return da.rio.clip_box(*bbox, crs="EPSG:4326").load()


def describe(granule):
    """Short facts about one photo: date, satellite, tile, and NASA's whole-tile cloud %."""
    name = granule["umm"]["GranuleUR"]  # e.g. HLS.L30.T17SPU.2018228T155252.v2.0
    parts = name.split(".")
    attrs = {a["Name"]: a["Values"][0] for a in granule["umm"].get("AdditionalAttributes", [])}
    date = np.datetime64(granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10])
    return {
        "date": date,
        "satellite": "Landsat" if parts[1] == "L30" else "Sentinel-2",
        "tile": parts[2],
        "tile_cloud_pct": float(attrs.get("CLOUD_COVERAGE", "nan")),
        "name": name,
    }


def box_pixels(bbox, crs):
    """How many 30 m pixels the WHOLE box holds, measured in the photo's own map grid."""
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = t.transform([bbox[0], bbox[2], bbox[0], bbox[2]], [bbox[1], bbox[1], bbox[3], bbox[3]])
    return (max(xs) - min(xs)) * (max(ys) - min(ys)) / (30 * 30)


def clear_fraction(fmask, bbox):
    """Share of the WHOLE box that the satellite saw AND is free of cloud and shadow.

    We divide by the whole box, not by the piece this tile happens to cover. (First version
    divided by the piece, so a tile touching only 2% of the box could score "97% clear".)
    Pixels with no data (past the tile's or the satellite's edge) count as not clear.
    """
    values = fmask.values
    seen = values != FMASK_NODATA
    clear = seen & ((values & FMASK_CLOUD_BITS) == 0)
    total = box_pixels(bbox, fmask.rio.crs)
    return min(clear.sum() / total, 1.0), min(seen.sum() / total, 1.0)


# ---------- Week 2: reflectance bands and water indexes ----------

# Band names differ between the two satellites. We give them plain-English names.
BANDS = {
    "Sentinel-2": {"red": "B04", "green": "B03", "blue": "B02", "nir": "B8A", "swir1": "B11", "swir2": "B12"},
    "Landsat": {"red": "B04", "green": "B03", "blue": "B02", "nir": "B05", "swir1": "B06", "swir2": "B07"},
}
REFLECTANCE_FILL = -9999  # HLS marks "no measurement" with this number


def find_photo(bbox, date, satellite):
    """The one HLS photo of the box on a given day from a given satellite (best-covering tile)."""
    code = ".S30." if satellite == "Sentinel-2" else ".L30."
    found = [g for g in search(bbox, date, date) if code in g["umm"]["GranuleUR"]]
    if not found:
        raise LookupError(f"no {satellite} photo on {date}")
    # If the box touches several tiles, keep the one covering the most of it.
    return max(found, key=lambda g: read_band(band_url(g, "Fmask"), bbox).size)


def read_reflectance(granule, bbox, satellite, names=("green", "nir", "swir1")):
    """Read bands as reflectance (share of light bounced back, 0 to 1). Fill values become NaN (blank)."""
    out = {}
    for name in names:
        da = read_band(band_url(granule, BANDS[satellite][name]), bbox).astype("float32")
        out[name] = da.where(da != REFLECTANCE_FILL) * 0.0001  # HLS stores reflectance x 10000
    return out


def usable_mask(fmask):
    """True where the satellite saw the ground with no cloud, cloud shadow, or cloud edge."""
    v = fmask.values
    return (v != FMASK_NODATA) & ((v & FMASK_CLOUD_BITS) == 0)


def normalized_difference(a, b):
    """(a - b) / (a + b): always between -1 and +1. Used by NDWI and MNDWI."""
    return (a - b) / (a + b)


def ndwi(bands):
    """Water index from green and near-infrared: water is bright green-ish, dark in NIR."""
    return normalized_difference(bands["green"], bands["nir"])


def mndwi(bands):
    """Modified water index: uses shortwave infrared instead of NIR, often better near buildings."""
    return normalized_difference(bands["green"], bands["swir1"])


# ---------- Burn-scar phase: burn index ----------

FMASK_WATER_BIT = 1 << 5  # Fmask's own guess that a pixel is water (lakes confuse the burn index)


def nbr(bands):
    """Normalized Burn Ratio from near-infrared and the longer shortwave infrared (swir2).

    Living leaves: bright in NIR, dark in SWIR, so NBR is high. Burned ground: the reverse, so NBR is low.
    """
    return normalized_difference(bands["nir"], bands["swir2"])
