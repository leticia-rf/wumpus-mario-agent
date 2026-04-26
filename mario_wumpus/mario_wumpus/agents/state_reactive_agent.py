from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept

from collections import deque


class StateAgent(BaseAgent):
    """
    Agente reativo com estados baseado em mapa:
    
    -> possui um mapa interno (dicionário) com os estados: 'visited', 'safe', 'pit', 'bowser', 
    'pit_candidates' e 'bowser_candidates' (conjuntos de celulas vizinhas candidatas)
    -> estratégia principal: prioriza exploração segura, usa inferências para identificar perigos, atira em Bowser quando possível
    
    atualização do mapa com percepções:
    - no primeiro turno, salva o valor de N do grid
    (usado para calcular a posicao de vizinhos validos, excluindo paredes)

    - marca a posição atual como visitada e segura
    - para cada vizinho:
      - se não há brisa, vizinhos não têm poços / se há brisa, adiciona vizinhos como candidatos a poço
      - se não há fedor, vizinhos não têm Bowser / se há fedor e Bowser não foi encontrado ainda, adiciona vizinhos como candidatos a Bowser
      - se não há brisa nem fedor, vizinhos são seguros

    - se há grito, Bowser foi morto: todas as células são seguras e candidatos a Bowser são limpos
    - após tiro sem grito, a célula alvo é marcada como segura
    
    inferências: 
    - reduz candidatos com base nas percepções atualizadas
    - se restar apenas um candidato para poço ou Bowser, marca como encontrado

    decisão de ação e movimentação:
    - se há brilho, executa RESCUE
    - se estava mirando, executa SHOOT
    - se há fedor e possui fireball, mira em Bowser conhecido ou candidato aleatório
    - busca via BFS a próxima célula segura não visitada
    - se não encontrar, arrisca mover para célula desconhecida
    - caso contrário, movimento aleatório    
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

    def reset(self) -> None:
        self.map.clear()
        self.N = None
        self.shot_position = None
        self.path = []
        self.is_aiming = False
        self.just_shot = False
 

    def _neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = pos
        neighbors = [] # vetor de tuplas com a posicao
        
        if row > 0:                            # celula de cima
            neighbors.append((row - 1, col))   
        if row < self.N:                       # celula de baixo
            neighbors.append((row + 1, col))
        if col > 0:                            # celula da esquerda
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

        # para cada vizinho, se nao esta no mapa, cria
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

        # BREEZE
        if not percept.breeze:
            for n in neighbors:
                self.map[n]["pit"] = False
        if percept.breeze:                                 # adiciona vizinhos como celulas condidatas
            cell["pit_candidates"] = { 
                n for n in neighbors 
                if self.map[n]["pit"] is not False and self.map[n]["safe"] is not True
            } 

        # STINK 
        if not percept.stink:
            for n in neighbors:
                self.map[n]["bowser"] = False
        if percept.stink and not any(c.get("bowser") is True for c in self.map.values()):
            cell["bowser_candidates"] = {
                n for n in neighbors
                if self.map[n]["bowser"] is not False and self.map[n]["safe"] is not True
            }   
        
        # safe
        if not percept.breeze and not percept.stink:
            for n in neighbors:
                self.map[n]["safe"] = True
        
        # SCREAM
        if percept.scream:
            for c in self.map.values():
                c["bowser"] = False
                c["safe"] = True
                c["bowser_candidates"].clear()
        elif self.just_shot and self.shot_position:        # se acabou de atirar e bowser nao morreu, celula esta segura
            self.map[self.shot_position]["bowser"] = False
            self.map[self.shot_position]["safe"] = True
            self.shot_position = None                      # reseta a posição e o estado do tiro
            self.just_shot = False

        # inferencias
        for p, c in self.map.items():
            if c["pit_candidates"]: 
                c["pit_candidates"] = { 
                    n for n in c["pit_candidates"] 
                    if self.map[n]["pit"] is not False and self.map[n]["safe"] is not True
                }
                if len(c["pit_candidates"]) == 1:          # se sobrou so 1 candidata, achou um poco
                    self.map[next(iter(c["pit_candidates"]))]["pit"] = True

            if c["bowser_candidates"]: 
                c["bowser_candidates"] = { 
                    n for n in c["bowser_candidates"] 
                    if self.map[n]["bowser"] is not False and self.map[n]["safe"] is not True
                }
                if len(c["bowser_candidates"]) == 1:       # se sobrou so 1 candidato, achou o bowser
                    self.map[next(iter(c["bowser_candidates"]))]["bowser"] = True
                    for c2 in self.map.values():
                        c2["bowser_candidates"].clear()

            if c["pit"] is False and c["bowser"] is False and c["safe"] is None:
                c["safe"] = True


    def _move_to(self, pos, target):
        d_row = target[0] - pos[0]
        d_col = target[1] - pos[1]

        if d_row < 0: return Action.MOVE_UP
        if d_row > 0: return Action.MOVE_DOWN
        if d_col > 0: return Action.MOVE_RIGHT
        if d_col < 0: return Action.MOVE_LEFT

    def _bfs_next_safe(self, start) -> None:
        queue = deque([start])
        parent = {start: None}

        while queue:
            current = queue.popleft()

            if (current != start                           # seguro não visitado (exceto o start)
                and self.map[current]["safe"] is True
                and self.map[current]["visited"] is False):

                while parent[current] != start:
                    current = parent[current]
                return current

            neighbors = self._neighbors(current)           
            self.rng.shuffle(neighbors)                    # embaralha a lista de vizinhos a cada execucao

            for n in neighbors:
                if n not in parent and self.map.get(n, {}).get("safe") is True:
                    parent[n] = current
                    queue.append(n)


    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        pos = percept.position.as_tuple()

        # RESCUE
        if percept.glitter:
            return Action.RESCUE
        
        self._update_map(percept)

        # SHOOT
        if self.is_aiming:
            self.is_aiming = False
            self.just_shot = True
            return Action.SHOOT 
        
        # AIM 
        if percept.stink and percept.has_fireball:
            bowser_known = [
                p for p, c in self.map.items()
                if c.get("bowser") is True
            ]
            if bowser_known:                               # mirar no bowser ja conhecido ou em uma das celulas candidatas
                target = bowser_known[0]
            else:
                targets = [
                    n for n in self.map.get(pos, {}).get("bowser_candidates", set())
                    if self.map.get(n, {}).get("bowser") is not False
                ]
                target = self.rng.choice(targets)

            self.shot_position = target
            self.is_aiming = True
            
            d_row = target[0] - pos[0]                     # calcula a direcao do alvo para mirar
            d_col = target[1] - pos[1]

            if d_row < 0: return Action.AIM_UP
            if d_row > 0: return Action.AIM_DOWN
            if d_col > 0: return Action.AIM_RIGHT
            if d_col < 0: return Action.AIM_LEFT
        
        # BFS
        next_pos = self._bfs_next_safe(pos)
        if next_pos:
            return self._move_to(pos, next_pos)
        
        # ARRISCAR
        valid_neighbors = self._neighbors(pos)
        unknown = [
            n for n in valid_neighbors
            if self.map.get(n, {}).get("safe") is None
            and self.map.get(n, {}).get("pit") is not True
            and self.map.get(n, {}).get("bowser") is not True
        ]
        if unknown:
            return self._move_to(pos, self.rng.choice(unknown))

        return self.rng.choice(
            [Action.MOVE_UP, Action.MOVE_RIGHT, Action.MOVE_DOWN, Action.MOVE_LEFT]
        )