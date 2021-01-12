from concurrent.futures import thread
from queue import Queue
from threading import Thread

from coordinates import Coordinates, random_coords_no_ocean

_queue = Queue(maxsize=50)


def _generate():
    while True:
        coords = random_coords_no_ocean()
        print(f'Generated {coords}')
        _queue.put(coords)


def init():
    Thread(target=_generate).start()


def get_random_coords() -> Coordinates:
    return _queue.get()

