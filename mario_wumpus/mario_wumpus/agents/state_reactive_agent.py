from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class StateAgent(BaseAgent):
    """
    Agente reativo com estados:

    mapa = visitado, seguro, possivel_poco, possivel_bowser
    comeca: mapa vazio, tudo FALSE, posicao inicial (N,1): visitado e seguro

    -> atualizar mapa percepcoes
       -> pegar vizinhos, excluindo as paredes
       -> marcar percepcoes

    -> decidir proxima celula a partir do mapa
       -> se nao conseguir decidir, arrisca

    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed) 
        self.map = {} # dicionario 
        self.N = None # null
        print("Agente Reativo com Estados!")
 

    def _neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = pos
        neighbors = [] # vetor de tuplas com a posicao
        
        # celula de cima
        if row > 1: 
            neighbors.append((row - 1, col)) # append adiciona ao final da lista

        # celula de baixo
        if self.N is None or row < self.N:
            neighbors.append((row + 1, col))

        # celula da esquerda
        if col > 1:
            neighbors.append((row, col - 1))

        # celula da direita
        if self.N is None or col < self.N:
            neighbors.append((row, col + 1))
        
        return neighbors


    def _update_map(self, percept: Percept) -> None:
        current_pos = percept.position.as_tuple()
        row, col = current_pos

        # descobre e armazena o tamanho do mapa logo no inicio
        if self.N is None:
            self.N = row
        
        # marca a posicao atual como visitada e segura
        self.mapa[current_pos]["visited"] = True
        self.mapa[current_pos]["safe"] = True

        neighbors = self._neighbors(current_pos)

        # ....


    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        
        if percept.glitter:
            return Action.RESCUE

        if percept.stink and percept.has_fireball:
            return Action.SHOOT
        

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