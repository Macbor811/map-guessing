from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from coordinates import Coordinates
from database import Base


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    password = Column(String(50), unique=False)
    games = relationship('Game', back_populates='user')

    def __init__(self, name: str, password: str):
        self.name = name
        self.password = password

    def __repr__(self):
        return '<User %r>' % self.name


game_coords_association = Table('game_coords_association', Base.metadata,
    Column('game_id', Integer, ForeignKey('game.id')),
    Column('coords_id', Integer, ForeignKey('coords.id'))
)


class Game(Base):
    __tablename__ = 'game'
    id = Column(Integer, primary_key=True)
    current_round = Column(Integer)
    rounds_count = Column(Integer)
    is_finished = Column(Boolean)
    is_ranked = Column(Boolean)
    score = Column(Float)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='games')
    coords = relationship("Coords", secondary=game_coords_association)


class Coords(Base):
    __tablename__ = 'coords'
    id = Column(Integer, primary_key=True)
    lat = Column(Float)
    lng = Column(Float)

    def to_coordinates(self) -> Coordinates:
        return Coordinates(self.lat, self.lng)



