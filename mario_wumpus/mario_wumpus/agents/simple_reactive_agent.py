from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class SimpleAgent(BaseAgent):
    """
    Agente reativo simples (decide a partir da percepção atual):
    - se 'glitter', 'RESCUE'
    - se 'stink' AND 'has_fireball', 'SHOOT'
    - se 'breeze' ou 'stink' ou 'bump', escolhe aleatoriamente uma direcao para mover, exceto a atual
    - senao, se move na mesma direcao
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed) 
        print("Agente Reativo Simples!")
 
    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        if percept.glitter:
            return Action.RESCUE

        if percept.stink and percept.has_fireball:
            return Action.SHOOT
        
        # dicionario
        move_actions = {
            'UP': Action.MOVE_UP,
            'RIGHT': Action.MOVE_RIGHT,
            'DOWN': Action.MOVE_DOWN,
            'LEFT': Action.MOVE_LEFT
        }
        current_move_action = move_actions[percept.facing.name]

        options = [
            Action.MOVE_UP,
            Action.MOVE_RIGHT,
            Action.MOVE_DOWN,
            Action.MOVE_LEFT,
            Action.WAIT,
        ]

        if percept.breeze or percept.stink or percept.bump:
            if current_move_action in options:
                options.remove(current_move_action)
            return self.rng.choice(options)
        
        return current_move_action