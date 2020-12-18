import asyncio

import PIL
import cv2
import geotiler
import numpy
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

from config import Configuration
from coordinates import random_coords, random_coords_no_ocean

app = Flask(__name__)
Bootstrap(app)

BING_KEY = Configuration().BING_KEY

@app.route('/')
def index():
    coords = random_coords_no_ocean()
    return render_template('index.html', coords=coords, bing_key=BING_KEY)


if __name__ == '__main__':
    app.run()
