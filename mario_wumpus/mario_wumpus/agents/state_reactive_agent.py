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

        self.shot_position = None
        self.path = []                        # pilha com o caminho percorrido
        self.is_aiming = False                # se mirou no turno anterior
        self.just_shot = False                # se atirou no turno atual

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

        # suspeitas -> adiciona vizinhos como candidatos
        if percept.breeze:
            cell["pit_candidates"] = { 
                n for n in neighbors 
                if self.map[n]["pit"] is not False and self.map[n]["safe"] is not True
            } 

        if percept.stink:
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

        # se bowser nao morreu e acabou de atirar
        elif self.just_shot and self.shot_position:
            self.map[self.shot_position]["bowser"] = False

        # reseta a posição e o estado do tiro
        self.shot_position = None
        self.just_shot = False


    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        pos = percept.position.as_tuple()
        row, col = pos

        if percept.glitter:
            return Action.RESCUE
        
        self._update_map(percept)

        if self.is_aiming:
            self.is_aiming = False
            self.just_shot = True
            return Action.SHOOT
        
        # no backtracking, ir removendo o caminho
        # nos outros return, ir adicionando o caminho
        

        valid_neighbors = self._neighbors(pos)

        if percept.stink and percept.has_fireball:
            targets = [                                    # celulas alvos, possiveis de ter o bowser
                n for n in self.map.get(pos, {}).get("bowser_candidates", set())
                if self.map.get(n, {}).get("bowser") is not False
            ]

            confirmed = [
                n for n in targets
                if self.map.get(n, {}).get("bowser") is True
            ]
            if confirmed:
                targets = confirmed

            if targets:
                target = self.rng.choice(targets)          # se tiver varios, escolhe um 
                self.shot_position = target
                self.is_aiming = True
                
                d_row = target[0] - pos[0]                 # calcula a direcao do alvo para mirar
                d_col = target[1] - pos[1]

                if d_row < 0: return Action.AIM_UP
                if d_row > 0: return Action.AIM_DOWN
                if d_col > 0: return Action.AIM_RIGHT
                if d_col < 0: return Action.AIM_LEFT

        """"
        candidates = [
            (Action.MOVE_UP, (row - 1, col)),
            (Action.MOVE_RIGHT, (row, col + 1)),
            (Action.MOVE_DOWN, (row + 1, col)),
            (Action.MOVE_LEFT, (row, col - 1)),
        ]

        valid_moves = [
            (act, p) for act, p in candidates 
            if p in valid_neighbors
        ]

        safe_unvisited = [
            (act, p) for act, p in valid_moves 
            if self.map[p]["safe"] is True and not self.map[p]["visited"]
        ]
        safe_visited = [
            (act, p) for act, p in valid_moves 
            if self.map[p]["safe"] is True
        ]
        unknown_moves = [
            (act, p) for act, p in valid_moves 
            if self.map[p]["safe"] is not True and self.map[p]["pit"] is not True and self.map[p]["bowser"] is not True
        ]

        if safe_unvisited:
            return self.rng.choice(safe_unvisited)[0]
        if safe_visited:
            return self.rng.choice(safe_visited)[0]
        if unknown_moves:
            return self.rng.choice(unknown_moves)[0]

        return self.rng.choice(valid_moves)[0] if valid_moves else Action.WAIT
        """