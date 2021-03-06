import asyncio
from random import uniform
import time
import geotiler
import numpy
import numpy as np
import cv2 as cv

LAT_RANGE = 80.0
LNG_RANGE = 180.0


class Coordinates:

    def __init__(self, lat: float, lng: float):
        self.lat = lat
        self.lng = lng

    def to_tuple(self) -> tuple[float, float]:
        return self.lat, self.lng

    def __str__(self):
        return f'({self.lat}, {self.lng})'


def random_coords() -> Coordinates:
    lat = uniform(-LAT_RANGE, LAT_RANGE)
    lng = uniform(-LNG_RANGE, LNG_RANGE)
    return Coordinates(round(lat, 3), round(lng, 3))


def countPixelsInRange(img: np.ndarray, min: list[int], max: list[int]) -> int:
    dst = cv.inRange(img, np.array(min, np.uint8), np.array(max, np.uint8))
    count = cv.countNonZero(dst)
    return count


def random_coords_no_ocean() -> Coordinates:

    WATER_COLOR = [223, 211, 170]

    asyncio.set_event_loop(asyncio.new_event_loop())
    resized: np.ndarray
    coords: Coordinates
    while True:
        coords = random_coords()
        map = geotiler.Map(center=(coords.lng, coords.lat), zoom=9, size=(1200, 800))
        image = geotiler.render_map(map).convert('RGB')
        open_cv_image = numpy.array(image)
        img = open_cv_image[:, :, ::-1].copy()

        scale_percent = 5  # percent of original size
        width = int(img.shape[1] * scale_percent / 100)
        height = int(img.shape[0] * scale_percent / 100)
        dim = (width, height)
        resized = cv.resize(img, dim, interpolation=cv.INTER_AREA)

        count = countPixelsInRange(resized, [x-5 for x in WATER_COLOR], [x+5 for x in WATER_COLOR])
        ratio = count / (resized.size / 3)

        if ratio < 0.9:
            return coords