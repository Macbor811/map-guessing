from enum import Enum
from flask import session


class SessionProperty(Enum):
    AUTH_USER = 'user'

    GAME = 'game'
    GAME_ACTUAL_COORDS = 'actual_coords'
    GAME_GUESSED_COORDS = 'guessed_coords'
    GAME_ROUND_NUMBER = 'round_number'
    GAME_SCORE = 'score'

    SETTINGS_ZOOM = 'zoom'
    SETTINGS_LABELS_ENABLED = 'labels_enabled'
    SETTINGS_ROUNDS_COUNT = 'rounds_count'

    def get(self, default=None):
        return session.get(self.value, default)

    def set(self, val):
        session[self.value] = val

    def clear(self):
        if self.value in session:
            session.pop(self.value)