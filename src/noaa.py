"""NOAA airplane photos of Hurricane Florence (NOAA National Geodetic Survey, Sept 15-22, 2018).

Used as an independent check ("answer key") on our maps. For the Lumber River box, the Sept 19
flights cover the town and river corridor; Sept 20 covers the downstream (southeast) part.
Photos come as standard web-map tiles (256 x 256 pixels). At zoom 17 one tile is about 300 m
across here, so one 30 m HLS pixel is about 25 tile pixels wide.
"""
import io
import math

import numpy as np
import requests
from PIL import Image

TILE_URL = "https://stormscdn.ngs.noaa.gov/{day}-rgb/{z}/{x}/{y}"
DAYS = ("20180919a", "20180919b", "20180919c", "20180920a", "20180920b", "20180920c")


def tile_xy(lon, lat, z=17):
    """Which tile holds this spot, and where inside the tile (pixel position) it falls."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y), (x % 1) * 256, (y % 1) * 256


def photo_at(lon, lat, z=17):
    """NOAA photo tile around a spot: (image, px, py, flight) or None if no flight covered it."""
    tx, ty, px, py = tile_xy(lon, lat, z)
    for day in DAYS:
        r = requests.get(TILE_URL.format(day=day, z=z, x=tx, y=ty), timeout=20)
        if r.status_code == 200 and len(r.content) > 2000:
            im = np.array(Image.open(io.BytesIO(r.content)).convert("RGBA"))
            if (im[..., 3] > 0).mean() > 0.9:  # mostly real photo, not the blank edge of a flight
                return im, px, py, day
    return None
