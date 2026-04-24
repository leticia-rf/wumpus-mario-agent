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
        self.last_shot_position = None
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
        # define o tamanho do mapa logo no primeiro turno
        if self.N is None:
            self.N = percept.position.row

        pos = percept.position.as_tuple()

        # insere posicao atual no mapa, se nao existia
        if pos not in self.map:
            self.map[pos] = {
                "visited": False,
                "safe": None,
                "pit": None,
                "bowser": None,
                "pit_candidates": set(),
                "bowser_candidates": set(),
            }

        cell = self.map[pos]

        # marca a posicao atual como visitada e segura
        cell["visited"] = True
        cell["safe"] = True
        cell["pit"] = False
        cell["bowser"] = False

        # para cada coordenada vizinha, se nao esta no mapa, cria
        neighbors = self._neighbors(pos)
        for n in neighbors: 
            if n not in self.map:
                self.map[n] = {
                    "visited": False,
                    "safe": None,
                    "pit": None,
                    "bowser": None,
                    "pit_candidates": set(),
                    "bowser_candidates": set(),
                }

        # vizinhos seguros
        if not percept.breeze:
            for n in neighbors:
                self.map[n]["pit"] = False
                
        if not percept.stink:
            for n in neighbors:
                self.map[n]["bowser"] = False

        if not percept.breeze and not percept.stink:
            for n in neighbors:
                self.map[n]["safe"] = True

        # suspeitas -> adiciona vizinhos como condidatos
        if percept.breeze:
            self.map[n]["bowser"] = False
            cell["pit_candidates"] = { 
                n for n in neighbors 
                if self.map[n]["pit"] is not False and self.map[n]["safe"] is not True
            } 

        if percept.stink:
            self.map[n]["pit"] = False
            cell["bowser_candidates"] = {
                n for n in neighbors
                if self.map[n]["bowser"] is not False and self.map[n]["safe"] is not True
            }

        # atualizacao global
        for p, c in self.map.items():
            if c["pit_candidates"]: 
                c["pit_candidates"] = { 
                    n for n in c["pit_candidates"] 
                    if self.map[n]["pit"] is not False and self.map[n]["safe"] is not True
                }
                # se sobrou so 1 candidato, achou o poco
                if len(c["pit_candidates"]) == 1: 
                    self.map[next(iter(c["pit_candidates"]))]["pit"] = True

            if c["bowser_candidates"]: 
                c["bowser_candidates"] = { 
                    n for n in c["bowser_candidates"] 
                    if self.map[n]["bowser"] is not False and self.map[n]["safe"] is not True
                }
                # se sobrou so 1 candidato, achou o bowser
                if len(c["bowser_candidates"]) == 1: 
                    self.map[next(iter(c["bowser_candidates"]))]["bowser"] = True

        # bowser morreu
        if percept.scream:
            for c in self.map.values():
                c["bowser"] = False
                c["bowser_candidates"].clear()
                if c["pit"] is False:                      # se a célula não tem poço, ela vira segura
                    c["safe"] = True

        # bowser nao morreu
        elif self.last_shot_position is not None:
            self.map[self.last_shot_position]["bowser"] = False

        # reseta a posição do tiro
        self.last_shot_position = None


    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        pos = percept.position.as_tuple()
        row, col = pos

        if percept.glitter:
            return Action.RESCUE
        
        self._update_map(percept)

        # atirar no bowser (mirar certo se estiver na parede)

        # continuar no mesmo sentido e
        # voltar quando vizinhos sao possiveis pocos e 
        # arriscar qnd nao tiver mais saida

        if percept.stink and percept.has_fireball:
            cell = self.map.get(pos, {})
            bowser_candidates = cell.get("bowser_candidates", set())

            # evita celulas ja provadas estar sem o bowser
            valid_targets = [
                n for n in bowser_candidates
                if self.map.get(n, {}).get("bowser") is not False
            ]

            if valid_targets:
                target = self.rng.choice(valid_targets)    # se tem varios, escolhe um
                self.last_shot_position = target
                
                return Action.SHOOT


        vizinhos_validos = self._neighbors(pos)

        candidates = [
            (Action.MOVE_UP, (row - 1, col)),
            (Action.MOVE_RIGHT, (row, col + 1)),
            (Action.MOVE_DOWN, (row + 1, col)),
            (Action.MOVE_LEFT, (row, col - 1)),
        ]

        valid_moves = [
            (act, p) for act, p in candidates 
            if p in vizinhos_validos
        ]

       