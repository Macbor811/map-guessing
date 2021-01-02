import asyncio
import re
from functools import wraps

import PIL
import cv2
import geotiler
import numpy
from flask import Flask, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap
from geopy.distance import distance

from flask_session import Session

from config import Configuration
from coordinates import random_coords, random_coords_no_ocean, Coordinates

app = Flask(__name__)
Bootstrap(app)
sesh = Session()

BING_KEY = Configuration().BING_KEY


def auth_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated


def parse_leaflet_latlng(text: str) -> Coordinates:
    regex = re.compile('LatLng\\((.+),(.+)\\)')
    match = regex.match(text)
    return Coordinates(float(match.group(1)), float(match.group(2)))


@app.route('/round/result')
@auth_required
def round_result():
    actual: Coordinates = session['actual_coords']
    guessed: Coordinates = session['guessed_coords']

    dist = round(distance(actual.to_tuple(), guessed.to_tuple()).meters / 1000, 2)
    session['round_number'] = session.get('round_number', 0) + 1
    session['score'] = session.get('score', 0.0) + dist

    return render_template('round_result.html',
                           actual_coords=session['actual_coords'],
                           guessed_coords=session['guessed_coords'],
                           round_number=session['round_number'],
                           distance=dist,
                           bing_key=BING_KEY
                           )


@app.route('/round', methods=['POST'])
@auth_required
def game_round():
    selected_coords = request.form['selectedCoords']
    session['guessed_coords'] = parse_leaflet_latlng(selected_coords)
    return redirect(url_for('round_result'))


@app.route('/game')
@auth_required
def game():
    if session.get('round_number', 0) >= 5:
        session['round_number'] = 0
        return render_template('game_result.html', score=session.get('score', 0.0))
    coords = random_coords_no_ocean()
    session['actual_coords'] = coords
    return render_template('round.html', coords=coords, bing_key=BING_KEY)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        user = ['admin', 'pass']

        if user is None:
            return render_template('login.html', message=f'User ${username} does not exist')
        else:
            if user[1] == password:
                session['user'] = username
                if username == 'admin':
                    session['is_admin'] = True
                else:
                    session['is_admin'] = False
                return redirect(url_for('index'))
            else:
                return render_template('login.html', message='Incorrect password')


@app.route('/')
@auth_required
def index():
    return render_template('index.html')

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
sesh.init_app(app)
if __name__ == '__main__':
    app.run()
