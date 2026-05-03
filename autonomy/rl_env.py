"""
Ambiente lunar para Reinforcement Learning do rover.

MDP:
  Estado  : (lat_norm, lon_norm, energia_norm, insol_norm, prob_gelo)
  Acao    : {0:N, 1:S, 2:E, 3:W}
  Reward  : ganho_ice_prob - custo_energia + bonus_descoberta
  Done    : energia <= 0 OU max_passos atingido

Por que RL aqui faz sentido:
  - Ambiente parcialmente observável (rover nao ve o mapa inteiro)
  - Greedy 1-step falha quando o melhor PSR requer atravessar região sem gelo
  - RL aprende a planejar rotas multi-step para PSRs distantes
"""

import numpy as np
import os


class LunarRoverEnv:
    def __init__(
        self,
        insolacao_map: np.ndarray,
        label_map: np.ndarray,
        prob_map: np.ndarray = None,
        energia_inicial: float = 100.0,
        max_passos: int = 200,
        pos_inicial: tuple = None,
        temp_subsolo_map: np.ndarray = None,
    ):
        self.insolacao_map    = insolacao_map
        self.label_map        = label_map
        self.H, self.W        = insolacao_map.shape
        self.temp_subsolo_map = temp_subsolo_map   # (H, W, 20) ou None

        # Mapa de probabilidade de gelo (do modelo CNN, se disponível)
        self.prob_map = prob_map if prob_map is not None else label_map.astype(np.float32)

        self.energia_inicial = energia_inicial
        self.max_passos      = max_passos
        self.pos_inicial     = pos_inicial

        # Espaço de ações
        self.n_acoes = 4
        self.acoes   = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1)}  # N,S,W,E
        self.nomes_acoes = {0: "N", 1: "S", 2: "W", 3: "E"}

        # Estado interno
        self.pos    = None
        self.energia = None
        self.passos  = None
        self.visitados = None
        self.ice_encontrado = None

        self.obs_dim = 6   # (lat_n, lon_n, energia_n, insol_n, prob_gelo, temp_sub_norm)

    # ─── Reset ────────────────────────────────────────────────────────────────

    def reset(self) -> np.ndarray:
        if self.pos_inicial is not None:
            self.pos = list(self.pos_inicial)
        else:
            # Começa em posição polar aleatória (onde provavelmente há gelo)
            # Usa 1/6 do eixo lat para delimitar as faixas polares de qualquer grade
            polar_band = max(1, self.H // 6)
            lat = (np.random.randint(0, polar_band)
                   if np.random.rand() > 0.5
                   else np.random.randint(self.H - polar_band, self.H))
            lon = np.random.randint(0, self.W)
            self.pos = [lat, lon]

        self.energia        = self.energia_inicial
        self.passos         = 0
        self.visitados      = set()
        self.ice_encontrado = 0.0

        return self._observacao()

    # ─── Step ─────────────────────────────────────────────────────────────────

    def step(self, acao: int) -> tuple:
        assert 0 <= acao < self.n_acoes, f"Acao invalida: {acao}"

        di, dj    = self.acoes[acao]
        nova_i    = np.clip(self.pos[0] + di, 0, self.H - 1)
        nova_j    = (self.pos[1] + dj) % self.W   # longitude é circular
        nova_pos  = [nova_i, nova_j]

        # Custo de energia baseado no terreno (PSRs têm menor insolação = mais energia p/ manter calor)
        insol      = float(self.insolacao_map[nova_i, nova_j])
        custo      = 1.0 + (1 - insol / 1361.0) * 0.5   # 1.0 a 1.5 por passo

        self.energia -= custo
        self.pos      = nova_pos
        self.passos  += 1

        # Probabilidade de gelo na nova posição
        prob_gelo = float(self.prob_map[nova_i, nova_j])

        # Temperatura subsuperficial a 1m — fria = mais estável para gelo
        # Normalizada: 0=muito frio (bom), 1=quente (ruim) → bônus = 1 - temp_sub_n
        if self.temp_subsolo_map is not None:
            temp_sub_n = float(self.temp_subsolo_map[nova_i, nova_j, 10]) / 300.0
            bonus_subsolo = max(0.0, 1.0 - temp_sub_n) * 0.4   # até +0.4 em PSRs frios
        else:
            bonus_subsolo = 0.0

        # Reward
        chave = (nova_i, nova_j)
        bonus_novo = 0.3 if chave not in self.visitados else 0.0   # exploração
        self.visitados.add(chave)

        delta_ice = max(0, prob_gelo - self.ice_encontrado * 0.9)
        self.ice_encontrado = max(self.ice_encontrado, prob_gelo)

        reward = (
            prob_gelo * 2.0      # recompensa principal: achar gelo
            + delta_ice * 1.0    # bônus por melhorar o melhor encontrado
            + bonus_novo         # bônus por explorar célula nova
            + bonus_subsolo      # bônus por subsolo frio (estabilidade do gelo)
            - custo * 0.1        # penalidade leve de energia
        )

        # Terminação
        done = self.energia <= 0 or self.passos >= self.max_passos

        info = {
            "pos": list(self.pos),
            "energia": self.energia,
            "prob_gelo": prob_gelo,
            "ice_max": self.ice_encontrado,
            "passos": self.passos,
        }

        return self._observacao(), float(reward), done, info

    # ─── Observação ───────────────────────────────────────────────────────────

    def _observacao(self) -> np.ndarray:
        i, j   = self.pos
        insol  = float(self.insolacao_map[i, j]) / 1361.0
        prob   = float(self.prob_map[i, j])
        lat_n  = (i / (self.H - 1)) * 2.0 - 1.0
        lon_n  = (j / (self.W - 1)) * 2.0 - 1.0
        ener_n = self.energia / self.energia_inicial

        # Temperatura subsuperficial a 1m normalizada por 300K (0=muito frio, 1=quente)
        if self.temp_subsolo_map is not None:
            temp_sub_n = float(self.temp_subsolo_map[i, j, 10]) / 300.0
        else:
            temp_sub_n = 0.5   # neutro se mapa indisponível

        return np.array([lat_n, lon_n, ener_n, insol, prob, temp_sub_n], dtype=np.float32)

    def render_pos(self) -> str:
        i, j = self.pos
        # Converte indice de grade para graus (assume grade centrada em 0/0)
        lat = round(i * 180.0 / self.H - 90.0, 1)
        lon = round(j * 360.0 / self.W - 180.0, 1)
        prob = self.prob_map[i, j]
        return f"lat={lat:+.1f} lon={lon:+.1f} energia={self.energia:.1f} prob_gelo={prob:.3f}"
