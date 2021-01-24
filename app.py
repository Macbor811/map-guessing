import re
import time
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
from services import user_service, game_service, coords_service
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
@in_game
def game_settings():
    if request.method == 'GET':
        return render_template('game_settings.html')
    else:
        game: Game
        if SessionProperty.GAME.value in session:
            game = SessionProperty.GAME.get()
        else:
            game = game_service.find_current_game(user_name=SessionProperty.AUTH_USER.get())
            if game is None:
                game = game_service.create_game(user_name=SessionProperty.AUTH_USER.get(),
                                                zoom=int(request.form['zoom']),
                                                is_ranked=False,
                                                rounds_count=int(request.form['roundsCount']),
                                                labels_enabled='labelsEnabled' in request.form,
                                                time_limit=int(request.form['timeLimit'])
                                                )
            SessionProperty.GAME.set(game)

        data.game = game

        return redirect(url_for('game'))


@app.route('/round/<int:nr>/result/')
@auth_required
@in_game
def round_result(nr: int):
    SessionProperty.GAME_ROUND_NUMBER.set(SessionProperty.GAME_ROUND_NUMBER.get(1) + 1)
    game: Game = data.game
    coords = game.coords[nr - 1]
    if not coords.is_finished:
        coords.is_finished = True;
        coords_service.save(coords)
        now = time.time()
        print(coords.finish_time)
        print(now)

        if coords.finish_time is not None and coords.finish_time < now:
            penalty_score = 10000.0
            SessionProperty.GAME_SCORE.set(SessionProperty.GAME_SCORE.get(0.0) + penalty_score)
            return render_template('round_result_dnf.html',
                                   penalty_score=penalty_score,
                                   actual_coords=SessionProperty.GAME_ACTUAL_COORDS.get(),
                                   round_number=nr,
                                   rounds_count=game.rounds_count,
                                   bing_key=BING_KEY
                                   )
        else:
            actual: Coordinates = SessionProperty.GAME_ACTUAL_COORDS.get()
            guessed: Coordinates = SessionProperty.GAME_GUESSED_COORDS.get()

            dist = round(distance(actual.to_tuple(), guessed.to_tuple()).meters / 1000, 2)

            coords.lat_guessed = guessed.lat
            coords.lng_guessed = guessed.lng
            coords_service.save(coords)
            SessionProperty.GAME_SCORE.set(SessionProperty.GAME_SCORE.get(0.0) + dist)

            return render_template('round_result.html',
                                   actual_coords=SessionProperty.GAME_ACTUAL_COORDS.get(),
                                   guessed_coords=SessionProperty.GAME_GUESSED_COORDS.get(),
                                   round_number=nr,
                                   rounds_count=game.rounds_count,
                                   distance=dist,
                                   bing_key=BING_KEY
                                   )
    else:
        actual: Coordinates = coords.actual_coordinates()
        guessed: Coordinates = coords.guessed_coordinates()

        dist = round(distance(actual.to_tuple(), guessed.to_tuple()).meters / 1000, 2)

        return render_template('round_result.html',
                               actual_coords=actual,
                               guessed_coords=guessed,
                               round_number=nr,
                               rounds_count=game.rounds_count,
                               distance=dist,
                               bing_key=BING_KEY
                               )


@app.route('/round/<int:nr>/time', methods=['POST'])
@auth_required
@in_game
def send_time(nr: int):
    game: Game = data.game
    coords = game.coords[nr - 1]
    if coords.finish_time is None:
        coords.finish_time = time.time() + game.time_limit
        coords_service.save(coords)
    return ('', 200)


@app.route('/round/<int:nr>', methods=['GET', 'POST'])
@auth_required
@in_game
def game_round(nr: int):
    game: Game = data.game
    coords = game.coords[nr - 1]
    if request.method == 'POST':
        selected_coords = request.form['selectedCoords']
        if selected_coords != 'no_result':
            SessionProperty.GAME_GUESSED_COORDS.set(parse_leaflet_latlng(selected_coords))
        return redirect(url_for('round_result', nr=nr))
    else:
        if coords.is_finished:
            return redirect(url_for('round_result', nr=nr))
        SessionProperty.GAME_ACTUAL_COORDS.set(coords.actual_coordinates())
        return render_template('round.html', coords=coords.actual_coordinates(), zoom=game.zoom, labels_enabled=game.labels_enabled, bing_key=BING_KEY, time_limit=game.time_limit)


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

    SessionProperty.GAME_SCORE.set(game.score)
    SessionProperty.GAME_ROUND_NUMBER.set(game.current_round)

    if game.current_round > game.rounds_count:
        game.is_finished = True
        save_game(game)

        SessionProperty.GAME.clear()
        SessionProperty.GAME_ROUND_NUMBER.clear()

        return render_template('game_result.html', score=game.score)
    else:
        save_game(game)
        return redirect(url_for('game_round', nr=game.current_round))


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


class Entry:
    def __init__(self, no: int, username: str, score: float):
        self.no = no
        self.username = username
        self.score = score


@app.route('/')
@auth_required
def index():
    games = game_service.get_top_games(n=20)

    entries = [Entry(no=i+1, username=game.user.name, score=game.score) for i, game in enumerate(games)]

    return render_template('index.html', entries=entries)


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
