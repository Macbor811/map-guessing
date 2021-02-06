import asyncio
import time

import geotiler
import numpy
import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt

from coordinates import random_coords


def showHist(img):
    color = ('b', 'g', 'r')
    for i, col in enumerate(color):
        histr = cv.calcHist([img], [i], None, [256], [0, 256])
        plt.plot(histr, color=col)
        plt.xlim([0, 256])
    plt.show()

def countPixelsInRange(img, min, max):
    dst = cv.inRange(img, np.array(min, np.uint8), np.array(max, np.uint8))
    count = cv.countNonZero(dst)
    return count


WATER_COLOR = [223, 211, 170]

start_time = time.time()
asyncio.set_event_loop(asyncio.new_event_loop())
resized: np.ndarray
while True:
    coords = random_coords()
    print(f'{coords.lat}, {coords.lng}')
    map = geotiler.Map(center=(coords.lng, coords.lat), zoom=9, size=(1200, 800))
    image = geotiler.render_map(map).convert('RGB')
    open_cv_image = numpy.array(image)
    img = open_cv_image[:, :, ::-1].copy()

    scale_percent = 5  # percent of original size
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv.resize(img, dim, interpolation=cv.INTER_AREA)

    print(resized.size)
    count = countPixelsInRange(resized, [x-5 for x in WATER_COLOR], [x+5 for x in WATER_COLOR])
    print(count)
    ratio = count / (resized.size / 3)
    print(ratio)
    if ratio < 0.9:
        break


cv.imwrite('map.png', resized)
print("--- %s seconds ---" % (time.time() - start_time))