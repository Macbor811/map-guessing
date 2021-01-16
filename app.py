import re
from functools import wraps
from threading import local

from flask import Flask, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap
from geopy.distance import distance

from flask_session import Session

import coords_generator
from config import Configuration
from coordinates import random_coords_no_ocean, Coordinates
from database import db_session, init_db
from models import User, Game
from services import user_service, game_service
from session_property import SessionProperty

app = Flask(__name__)
Bootstrap(app)
sesh = Session()

BING_KEY = Configuration().BING_KEY

data = local()


def auth_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if SessionProperty.AUTH_USER.value not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated


def save_game(game: Game):
    game.score = SessionProperty.GAME_SCORE.get(0.0)
    game.current_round = SessionProperty.GAME_ROUND_NUMBER.get(1)
    game.rounds_count = SessionProperty.SETTINGS_ROUNDS_COUNT.get(5)
    game_service.save(game)


def in_game(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        game: Game
        if SessionProperty.GAME.value in session:
            game = SessionProperty.GAME.get()
        else:
            game = game_service.create_game(user_name=SessionProperty.AUTH_USER.get())
        data.game = game
        ret = func(*args, **kwargs)
        save_game(game)
        return ret
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


@app.route('/round/<int:nr>/result/')
@auth_required
@in_game
def round_result(nr: int):
    actual: Coordinates = SessionProperty.GAME_ACTUAL_COORDS.get()
    guessed: Coordinates = SessionProperty.GAME_GUESSED_COORDS.get()

    dist = round(distance(actual.to_tuple(), guessed.to_tuple()).meters / 1000, 2)
    SessionProperty.GAME_ROUND_NUMBER.set(SessionProperty.GAME_ROUND_NUMBER.get(1) + 1)
    SessionProperty.GAME_SCORE.set(SessionProperty.GAME_SCORE.get(0.0) + dist)

    return render_template('round_result.html',
                           actual_coords=SessionProperty.GAME_ACTUAL_COORDS.get(),
                           guessed_coords=SessionProperty.GAME_GUESSED_COORDS.get(),
                           round_number=nr,
                           rounds_count=SessionProperty.SETTINGS_ROUNDS_COUNT.get(),
                           distance=dist,
                           bing_key=BING_KEY
                           )


@app.route('/round/<int:nr>', methods=['GET', 'POST'])
@auth_required
@in_game
def game_round(nr: int):
    if request.method == 'POST':
        selected_coords = request.form['selectedCoords']
        SessionProperty.GAME_GUESSED_COORDS.set(parse_leaflet_latlng(selected_coords))
        return redirect(url_for('round_result', nr=nr))
    else:
        game: Game = data.game
        coords = game.coords[nr - 1].to_coordinates()
        SessionProperty.GAME_ACTUAL_COORDS.set(coords)
        zoom = SessionProperty.SETTINGS_ZOOM.get(9)
        labels_enabled = SessionProperty.SETTINGS_LABELS_ENABLED.get(True)
        return render_template('round.html', coords=coords, zoom=zoom, labels_enabled=labels_enabled, bing_key=BING_KEY)


@app.route('/game')
@auth_required
def game():

    game: Game
    if SessionProperty.GAME.value in session:
        game = SessionProperty.GAME.get()
    else:
        game = game_service.find_current_game(user_name=SessionProperty.AUTH_USER.get())
        if game is None:
            game = game_service.create_game(user_name=SessionProperty.AUTH_USER.get())
        SessionProperty.GAME.set(game)

    data.game = game

    SessionProperty.SETTINGS_ROUNDS_COUNT.set(game.rounds_count)
    SessionProperty.GAME_SCORE.set(game.score)
    SessionProperty.GAME_ROUND_NUMBER.set(game.current_round)

    if game.current_round > game.rounds_count:
        game.is_finished = True
        save_game(game)

        SessionProperty.GAME.clear()
        SessionProperty.GAME_ROUND_NUMBER.clear()
        SessionProperty.SETTINGS_ZOOM.clear()
        SessionProperty.SETTINGS_LABELS_ENABLED.clear()
        SessionProperty.SETTINGS_ROUNDS_COUNT.clear()

        return render_template('game_result.html', score=SessionProperty.GAME_SCORE.get())
    else:
        save_game(game)
        return redirect(url_for('game_round', nr=SessionProperty.GAME_ROUND_NUMBER.get(1)))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        user: User = user_service.find_by_name(username)

        if user is None:
            return render_template('login.html', message=f'User ${username} does not exist')
        else:
            if user.password == password:
                SessionProperty.AUTH_USER.set(username)
                if username == 'admin':
                    session['is_admin'] = True
                else:
                    session['is_admin'] = False
                return redirect(url_for('index'))
            else:
                return render_template('login.html', message='Incorrect password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form['username']
        password = request.form['password']

        user = user_service.find_by_name(username)

        if user is not None:
            return render_template('register.html', message=f'User {username} already exists')
        elif not any(c.isalpha() for c in username):
            return render_template('register.html', message='Username must contain at least one letter')
        else:
            user = User(username, password)
            user_service.save(user)
            return redirect(url_for('login', message=f'User {username} created'))


@app.route('/logout')
@auth_required
def logout():
    if 'user' in session:
        session.clear()
    return redirect(url_for('login'))


@app.route('/')
@auth_required
def index():
    return render_template('index.html')


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
sesh.init_app(app)
coords_generator.init()
init_db()
admin = user_service.find_by_name('admin')

if admin is None:
    admin = User('admin', 'pass')
    user_service.save(admin)

if __name__ == '__main__':
    app.run()
