"""Height of the ground for every pixel, from NASA's NASADEM height map.

NASADEM is a 30 m map of ground height (a "DEM": digital elevation model), measured by radar
from the Space Shuttle in February 2000. Hills do not move, so an old map is fine.
Files come as 1 x 1 degree squares, zipped. They are saved in data/dem/ (git-ignored).
"""
import zipfile
from pathlib import Path

import earthaccess
import numpy as np
import rioxarray
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = ROOT / "data" / "dem"


def height_files(bbox):
    """Download (once) the NASADEM squares touching the box. Returns the unzipped .hgt files."""
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    found = earthaccess.search_data(short_name="NASADEM_HGT", version="001", bounding_box=bbox)
    if not found:
        raise LookupError("no NASADEM file covers this box")
    paths = []
    for g in found:
        name = g["umm"]["GranuleUR"]  # e.g. NASADEM_HGT_n35w083
        hgt = DEM_DIR / (name.split("_")[-1] + ".hgt")
        if not hgt.exists():
            zip_path = Path(earthaccess.download([g], str(DEM_DIR))[0])
            with zipfile.ZipFile(zip_path) as z:
                # Take only the height file itself, and write it under a name we chose.
                member = next(m for m in z.namelist() if m.lower().endswith(".hgt"))
                hgt.write_bytes(z.read(member))
        paths.append(hgt)
    return paths


def height_like(band, bbox):
    """Ground height in metres on exactly the same pixel grid as a photo band."""
    files = height_files(bbox)
    if len(files) != 1:
        raise NotImplementedError("this box needs more than one height square; join them first")
    dem = rioxarray.open_rasterio(files[0], masked=True).squeeze("band", drop=True)
    # The height map is in longitude/latitude; the photo is on a metre grid. "Bilinear" blends
    # the four nearest height values, which suits a smooth surface like the ground.
    return dem.rio.reproject_match(band, resampling=Resampling.bilinear).values.astype("float32")


def slope_facing(height, pixel_m=30):
    """Which way each slope faces, as a compass label (N, E, S, W), and how steep it is in degrees."""
    d_south, d_east = np.gradient(height, pixel_m)  # rows run north -> south, columns west -> east
    steep = np.degrees(np.arctan(np.hypot(d_south, d_east)))
    # Downhill direction: opposite to the direction in which the ground rises.
    angle = np.degrees(np.arctan2(-d_east, d_south)) % 360  # 0 = faces north, 90 = east
    facing = np.array(["N", "E", "S", "W"])[((angle + 45) // 90).astype(int) % 4]
    return facing, steep
