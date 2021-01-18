from sqlalchemy import and_

import coords_generator
from database import db_session
from models import User, Game, Coords


class UserService:

    def find_by_name(self, name: str) -> User:
        return User.query.filter(User.name == name).first()

    def save(self, user: User):
        db_session.add(user)
        db_session.commit()


user_service = UserService()


class GameService:

    def find_current_game(self, user_name: str) -> Game:
        user = user_service.find_by_name(user_name)
        game = Game.query.filter(and_(Game.user == user, Game.is_finished == False)).first()
        return game

    def save(self, game: Game):
        db_session.add(game)
        db_session.commit()

    def create_game(self, user_name: str, rounds_count=5, is_ranked=True) -> Game:
        game = Game()
        game.user = user_service.find_by_name(user_name)
        game.rounds_count = rounds_count
        game.is_ranked = is_ranked
        game.current_round = 1
        game.score = 0.0

        for i in range(0, game.rounds_count):
            coordinates = coords_generator.get_random_coords()
            coords = Coords(lat=coordinates.lat, lng=coordinates.lng)
            game.coords.append(coords)

        db_session.add(game)
        db_session.commit()
        return game

    def get_top_games(self, n: int):
        return Game.query.filter(and_(Game.is_finished == True, Game.is_ranked == True)).order_by(Game.score).limit(n).all()


game_service = GameService()

# game = game_service.find_current_game(SessionProperty.AUTH_USER.get())
#
# if game is None:
#     game = game_service.create_game(user_name=SessionProperty.AUTH_USER.get())
# else:
#     if game.is_finished:
#         return render_template('game_result.html', score=game.score)
#
# return redirect(url_for('game_round', nr=game.current_round))
