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
       -> pega os vizinhos (ja excluindo as paredes)
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
        
        if row > 1:                            # celula de cima
            neighbors.append((row - 1, col))   
        if row < self.N:                       # celula de baixo
            neighbors.append((row + 1, col))
        if col > 1:                            # celula da esquerda
            neighbors.append((row, col - 1))
        if col < self.N:                       # celula da direita
            neighbors.append((row, col + 1))
        
        return neighbors # retorna a lista de coordenadas das celulas vizinhas

    def _update_map(self, percept: Percept) -> None:
        pos = percept.position.as_tuple()

        # insere posicao atual no mapa, se nao existia
        if pos not in self.map:
            cell = self.map.setdefault(pos, {
                "visited": False,
                "safe": None,
                "pit": None,
                "bowser": None,
                "pit_candidates": set(),
                "bowser_candidates": set(),
            })

        # marca a posicao atual como visitada e segura
        cell["visited"] = True
        cell["safe"] = True
        cell["pit"] = False
        cell["bowser"] = False

        # para cada coordenada vizinha, se nao esta no mapa, cria
        neighbors = self._neighbors(pos)
        for n in neighbors: 
            self.map.setdefault(n, {
                "visited": False,
                "safe": None,
                "pit": None,
                "bowser": None,
                "pit_candidates": set(),
                "bowser_candidates": set(),
            })
        
        # PIT (breeze)
        if percept.breeze:
            cell["pit_candidates"] = { 
                n for n in neighbors                       # adiciona vizinho como condidato 
                if self.map[n]["pit"] is not False         # se pit ja nao esta marcado como falso
            }
        else:
            for n in neighbors:
                self.map[n]["pit"] = False

        # BOWSER (stink)
        if percept.stink:
            cell["bowser_candidates"] = {
                n for n in neighbors
                if self.map[n]["bowser"] is not False
            }
        else:
            for n in neighbors:
                self.map[n]["bowser"] = False

        # safe
        if not percept.breeze and not percept.stink:
            for n in neighbors:
                self.map[n]["safe"] = True

        # limpeza + inferencia global
        for pos, ccell in self.map.items():                # para cada item do mapa

            if ccell["pit_candidates"]: 
                ccell["pit_candidates"] = { 
                    n for n in ccell["pit_candidates"]     # atualiza candidatas com pit ainda nao falso
                    if self.map[n]["pit"] is not False 
                }
                if len(ccell["pit_candidates"]) == 1:      # se sobrou somente uma candidata, marca pit como true
                    self.map[next(iter(ccell["pit_candidates"]))]["pit"] = True

            if ccell.get("bowser_candidates"):
                if ccell["bowser_candidates"]: 
                    ccell["bowser_candidates"] = { 
                        n for n in ccell["bowser_candidates"] 
                        if self.map[n]["bowser"] is not False 
                    }
                if len(ccell["bowser_candidates"]) == 1: 
                    self.map[next(iter(ccell["bowser_candidates"]))]["bowser"] = True


    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        # descobre e armazena o tamanho do mapa
        if self.N is None:
            self.N = percept.position.row

        # atualiza o mapa
        self._update_map(percept)


        # return self._choose_action(percept)

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