"""NOAA airplane photos of Hurricane Florence (NOAA National Geodetic Survey, Sept 15-22, 2018).

Used as an independent check ("answer key") on our maps. For the Lumber River box, the Sept 19
flights cover the town and river corridor; Sept 20 covers the downstream (southeast) part.
Photos come as standard web-map tiles (256 x 256 pixels). At zoom 17 and this latitude one tile
pixel is about 0.98 m, so a tile is about 250 m across and one 30 m HLS pixel is about 30 tile
pixels wide.
"""
import io
import math

import numpy as np
import requests
from PIL import Image, ImageDraw

TILE_URL = "https://stormscdn.ngs.noaa.gov/{day}-rgb/{z}/{x}/{y}"
DAYS = ("20180919a", "20180919b", "20180919c", "20180920a", "20180920b", "20180920c")
ZOOM = 17
_session = requests.Session()
_cache = {}


def metres_per_pixel(lat, z=ZOOM):
    """Ground size of one tile pixel (web maps stretch more toward the poles)."""
    return 156543.03392 * math.cos(math.radians(lat)) / 2 ** z


def tile_xy(lon, lat, z=ZOOM):
    """Which tile holds this spot, and where inside the tile (pixel position) it falls."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y), (x % 1) * 256, (y % 1) * 256


def get_tile(day, x, y, z=ZOOM):
    """One tile as an RGBA array, or None if that flight has no photo there. Remembered once fetched."""
    key = (day, x, y, z)
    if key not in _cache:
        r = _session.get(TILE_URL.format(day=day, z=z, x=x, y=y), timeout=30)
        im = None
        if r.status_code == 200 and len(r.content) > 2000:
            im = np.array(Image.open(io.BytesIO(r.content)).convert("RGBA"))
            if (im[..., 3] > 0).mean() < 0.9:  # mostly blank: the edge of a flight
                im = None
        _cache[key] = im
    return _cache[key]


def photo_at(lon, lat, z=ZOOM):
    """NOAA photo tile around a spot: (image, px, py, flight) or None if no flight covered it."""
    tx, ty, px, py = tile_xy(lon, lat, z)
    for day in DAYS:
        im = get_tile(day, tx, ty, z)
        if im is not None:
            return im, px, py, day
    return None


def chip(lon, lat, size=300, z=ZOOM):
    """A size x size photo centered on the spot (stitched from up to 9 tiles), with a yellow
    square the size of one 30 m HLS pixel. Returns (PIL image, flight) or None."""
    first = photo_at(lon, lat, z)
    if first is None:
        return None
    _, _, _, day = first
    tx, ty, px, py = tile_xy(lon, lat, z)
    mosaic = np.full((768, 768, 4), 128, np.uint8)  # 3 x 3 tiles; grey where a neighbour is missing
    mosaic[..., 3] = 255
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            t = get_tile(day, tx + dx, ty + dy, z)
            if t is not None:
                mosaic[(dy + 1) * 256:(dy + 2) * 256, (dx + 1) * 256:(dx + 2) * 256] = t
    cx, cy = 256 + px, 256 + py
    half = size // 2
    img = Image.fromarray(mosaic[int(cy) - half:int(cy) + half, int(cx) - half:int(cx) + half, :3])
    side = 30 / metres_per_pixel(lat, z)  # one 30 m pixel, in photo pixels
    d = ImageDraw.Draw(img)
    d.rectangle([half - side / 2, half - side / 2, half + side / 2, half + side / 2], outline=(255, 230, 0), width=3)
    return img, day
