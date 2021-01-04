import asyncio
import re
from enum import Enum
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
from session_property import SessionProperty

app = Flask(__name__)
Bootstrap(app)
sesh = Session()

BING_KEY = Configuration().BING_KEY


def auth_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if SessionProperty.AUTH_USER.value not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated


def parse_leaflet_latlng(text: str) -> Coordinates:
    regex = re.compile('LatLng\\((.+),(.+)\\)')
    match = regex.match(text)
    return Coordinates(float(match.group(1)), float(match.group(2)))


@app.route('/game-settings', methods=['GET', 'POST'])
@auth_required
def game_settings():
    if request.method == 'GET':
        return render_template('game_settings.html')
    else:
        zoom = request.form['zoom']
        rounds_count = request.form['roundsCount']
        labels_enabled = 'labelsEnabled' in request.form

        SessionProperty.SETTINGS_ZOOM.set(int(zoom))
        SessionProperty.SETTINGS_LABELS_ENABLED.set(labels_enabled)
        SessionProperty.SETTINGS_ROUNDS_COUNT.set(int(rounds_count))

        return redirect(url_for('game'))


@app.route('/round/result')
@auth_required
def round_result():
    actual: Coordinates = SessionProperty.GAME_ACTUAL_COORDS.get()
    guessed: Coordinates = SessionProperty.GAME_GUESSED_COORDS.get()

    dist = round(distance(actual.to_tuple(), guessed.to_tuple()).meters / 1000, 2)
    SessionProperty.GAME_ROUND_NUMBER.set(SessionProperty.GAME_ROUND_NUMBER.get(0) + 1)
    SessionProperty.GAME_SCORE.set(SessionProperty.GAME_SCORE.get(0.0) + dist)

    return render_template('round_result.html',
                           actual_coords=SessionProperty.GAME_ACTUAL_COORDS.get(),
                           guessed_coords=SessionProperty.GAME_GUESSED_COORDS.get(),
                           round_number=SessionProperty.GAME_ROUND_NUMBER.get(),
                           rounds_count=SessionProperty.SETTINGS_ROUNDS_COUNT.get(),
                           distance=dist,
                           bing_key=BING_KEY
                           )


@app.route('/round', methods=['POST'])
@auth_required
def game_round():
    selected_coords = request.form['selectedCoords']
    SessionProperty.GAME_GUESSED_COORDS.set(parse_leaflet_latlng(selected_coords))
    return redirect(url_for('round_result'))


@app.route('/game')
@auth_required
def game():
    rounds_count = SessionProperty.SETTINGS_ROUNDS_COUNT.get(5)
    SessionProperty.SETTINGS_ROUNDS_COUNT.set(rounds_count)

    if SessionProperty.GAME_ROUND_NUMBER.get(0) >= rounds_count:
        SessionProperty.GAME_ROUND_NUMBER.set(0)

        SessionProperty.SETTINGS_ZOOM.clear()
        SessionProperty.SETTINGS_LABELS_ENABLED.clear()
        SessionProperty.SETTINGS_ROUNDS_COUNT.clear()

        return render_template('game_result.html', score=SessionProperty.GAME_SCORE.get(0.0))
    coords = random_coords_no_ocean()
    SessionProperty.GAME_ACTUAL_COORDS.set(coords)
    zoom = SessionProperty.SETTINGS_ZOOM.get(9)
    labels_enabled = SessionProperty.SETTINGS_LABELS_ENABLED.get(True)
    return render_template('round.html', coords=coords, zoom=zoom, labels_enabled=labels_enabled, bing_key=BING_KEY)


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
                SessionProperty.AUTH_USER.set(username)
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
