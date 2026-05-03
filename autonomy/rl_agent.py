"""
DQN (Deep Q-Network) para navegação autônoma do rover lunar.

Arquitetura: MLP simples (estado contínuo, ação discreta)
  - Replay buffer para estabilidade
  - Target network com soft update
  - Epsilon-greedy para exploração

Estado (6 valores): [lat_norm, lon_norm, energia_norm, insol_norm, prob_gelo, temp_sub_norm]
Ações: {0:N, 1:S, 2:W, 3:E}
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random


# ─── Rede Q ───────────────────────────────────────────────────────────────────

class QNetwork(nn.Module):
    def __init__(self, obs_dim: int = 6, n_acoes: int = 4, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Linear(hidden // 2, n_acoes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ─── Replay Buffer ────────────────────────────────────────────────────────────

class ReplayBuffer:
    def __init__(self, capacity: int = 10_000):
        self.buffer = deque(maxlen=capacity)

    def push(self, obs, acao, reward, obs_next, done):
        self.buffer.append((obs, acao, reward, obs_next, float(done)))

    def sample(self, batch_size: int) -> tuple:
        batch = random.sample(self.buffer, batch_size)
        obs, acoes, rewards, obs_next, dones = zip(*batch)
        return (
            np.array(obs,      dtype=np.float32),
            np.array(acoes,    dtype=np.int64),
            np.array(rewards,  dtype=np.float32),
            np.array(obs_next, dtype=np.float32),
            np.array(dones,    dtype=np.float32),
        )

    def __len__(self):
        return len(self.buffer)


# ─── Agente DQN ───────────────────────────────────────────────────────────────

class DQNAgent:
    def __init__(
        self,
        obs_dim:        int   = 6,
        n_acoes:        int   = 4,
        lr:             float = 1e-3,
        gamma:          float = 0.99,
        epsilon_start:  float = 1.0,
        epsilon_end:    float = 0.05,
        epsilon_decay:  int   = 5_000,
        batch_size:     int   = 64,
        target_update:  int   = 100,
        buffer_capacity:int   = 10_000,
        device:         str   = "cpu",
    ):
        self.device       = torch.device(device)
        self.n_acoes      = n_acoes
        self.gamma        = gamma
        self.batch_size   = batch_size
        self.target_update = target_update

        self.q_net     = QNetwork(obs_dim, n_acoes).to(self.device)
        self.q_target  = QNetwork(obs_dim, n_acoes).to(self.device)
        self.q_target.load_state_dict(self.q_net.state_dict())
        self.q_target.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.buffer    = ReplayBuffer(capacity=buffer_capacity)

        self.epsilon       = epsilon_start
        self.epsilon_end   = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.steps_done    = 0

    # ─── Seleção de ação (epsilon-greedy) ─────────────────────────────────────

    def selecionar_acao(self, obs: np.ndarray) -> int:
        self.epsilon = self.epsilon_end + (1.0 - self.epsilon_end) * \
            np.exp(-self.steps_done / self.epsilon_decay)
        self.steps_done += 1

        if random.random() < self.epsilon:
            return random.randrange(self.n_acoes)

        with torch.no_grad():
            obs_t = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            return self.q_net(obs_t).argmax(dim=1).item()

    # ─── Passo de treino ──────────────────────────────────────────────────────

    def treinar(self) -> float | None:
        if len(self.buffer) < self.batch_size:
            return None

        obs, acoes, rewards, obs_next, dones = self.buffer.sample(self.batch_size)

        obs_t      = torch.tensor(obs,      device=self.device)
        acoes_t    = torch.tensor(acoes,    device=self.device)
        rewards_t  = torch.tensor(rewards,  device=self.device)
        obs_next_t = torch.tensor(obs_next, device=self.device)
        dones_t    = torch.tensor(dones,    device=self.device)

        # Q atual
        q_values = self.q_net(obs_t).gather(1, acoes_t.unsqueeze(1)).squeeze(1)

        # Q target (Double DQN: seleciona ação com q_net, avalia com q_target)
        with torch.no_grad():
            melhores_acoes = self.q_net(obs_next_t).argmax(dim=1, keepdim=True)
            q_next = self.q_target(obs_next_t).gather(1, melhores_acoes).squeeze(1)
            q_target = rewards_t + self.gamma * q_next * (1 - dones_t)

        loss = nn.SmoothL1Loss()(q_values, q_target)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.optimizer.step()

        return loss.item()

    # ─── Soft update do target network ────────────────────────────────────────

    def atualizar_target(self, tau: float = 0.005):
        for param, target_param in zip(self.q_net.parameters(), self.q_target.parameters()):
            target_param.data.copy_(tau * param.data + (1 - tau) * target_param.data)

    def salvar(self, path: str = "model/rl_pesos.pth"):
        torch.save({
            "q_net": self.q_net.state_dict(),
            "q_target": self.q_target.state_dict(),
            "steps": self.steps_done,
            "epsilon": self.epsilon,
        }, path)

    def carregar(self, path: str = "model/rl_pesos.pth"):
        ck = torch.load(path, map_location=self.device, weights_only=True)
        self.q_net.load_state_dict(ck["q_net"])
        self.q_target.load_state_dict(ck["q_target"])
        self.steps_done = ck.get("steps", 0)
        self.epsilon    = ck.get("epsilon", self.epsilon_end)
