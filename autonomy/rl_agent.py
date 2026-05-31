"""
DQN (Deep Q-Network) para navegação autônoma do rover lunar.

Arquitetura: MLP simples (estado contínuo, ação discreta)
  - Prioritized Experience Replay (PER) com sum-tree
  - Double DQN: seleciona ação com q_net, avalia com q_target
  - Target network com soft update (τ=0.005)
  - Epsilon-greedy com decaimento exponencial

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


# ─── Prioritized Replay Buffer (PER) ─────────────────────────────────────────

class SumTree:
    """
    Árvore binária onde cada nó pai = soma dos filhos.
    Permite amostragem proporcional à prioridade em O(log N).
    """
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree     = np.zeros(2 * capacity, dtype=np.float64)
        self.data     = np.empty(capacity, dtype=object)
        self.ptr      = 0
        self.size     = 0

    def _propagate(self, idx: int, delta: float) -> None:
        parent = idx // 2
        while parent >= 1:
            self.tree[parent] += delta
            parent //= 2

    def update(self, idx: int, priority: float) -> None:
        leaf = idx + self.capacity
        delta = priority - self.tree[leaf]
        self.tree[leaf] = priority
        self._propagate(leaf, delta)

    def add(self, priority: float, data) -> None:
        self.data[self.ptr] = data
        self.update(self.ptr, priority)
        self.ptr  = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def get(self, s: float) -> tuple[int, float, object]:
        """Retorna (índice, prioridade, dado) para valor s ∈ [0, total]."""
        idx = 1
        while idx < self.capacity:
            left = 2 * idx
            if s <= self.tree[left]:
                idx = left
            else:
                s -= self.tree[left]
                idx = left + 1
        data_idx = idx - self.capacity
        return data_idx, self.tree[idx], self.data[data_idx]

    @property
    def total(self) -> float:
        return self.tree[1]


class PrioritizedReplayBuffer:
    """
    PER (Schaul et al. 2016): amostragem proporcional à prioridade |δ|^α.
    Importance-sampling weights corrigem o viés: w_i = (1/N · 1/P(i))^β.
    α=0.6, β annealing 0.4→1.0 ao longo do treino.
    """
    def __init__(
        self,
        capacity: int   = 10_000,
        alpha:    float = 0.6,
        beta:     float = 0.4,
        beta_end: float = 1.0,
        beta_steps: int = 100_000,
        eps:      float = 1e-6,
    ):
        self.tree      = SumTree(capacity)
        self.alpha     = alpha
        self.beta      = beta
        self.beta_end  = beta_end
        self.beta_steps = beta_steps
        self.eps       = eps
        self._step     = 0
        self._max_prio = 1.0

    def push(self, obs, acao, reward, obs_next, done) -> None:
        self.tree.add(self._max_prio ** self.alpha,
                      (obs, acao, reward, obs_next, float(done)))

    def sample(self, batch_size: int) -> tuple:
        # β annealing linear
        self._step += 1
        self.beta = min(self.beta_end,
                        self.beta + (self.beta_end - self.beta) / self.beta_steps)

        indices, priorities, batch = [], [], []
        segment = self.tree.total / batch_size

        for i in range(batch_size):
            s    = random.uniform(i * segment, (i + 1) * segment)
            idx, prio, data = self.tree.get(s)
            if data is None:
                idx, prio, data = 0, self.eps, self.tree.data[0]
            indices.append(idx)
            priorities.append(prio)
            batch.append(data)

        # Importance-sampling weights
        probs   = np.array(priorities, dtype=np.float64) / (self.tree.total + 1e-10)
        weights = (self.tree.size * probs) ** (-self.beta)
        weights /= weights.max() + 1e-10
        weights  = weights.astype(np.float32)

        obs, acoes, rewards, obs_next, dones = zip(*batch)
        return (
            np.array(obs,      dtype=np.float32),
            np.array(acoes,    dtype=np.int64),
            np.array(rewards,  dtype=np.float32),
            np.array(obs_next, dtype=np.float32),
            np.array(dones,    dtype=np.float32),
            np.array(indices,  dtype=np.int64),
            weights,
        )

    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray) -> None:
        for idx, err in zip(indices, td_errors):
            prio = (abs(float(err)) + self.eps) ** self.alpha
            self._max_prio = max(self._max_prio, prio)
            self.tree.update(int(idx), prio)

    def __len__(self) -> int:
        return self.tree.size


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
        self.buffer    = PrioritizedReplayBuffer(capacity=buffer_capacity)

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

    # ─── Passo de treino (com IS weights do PER) ──────────────────────────────

    def treinar(self) -> float | None:
        if len(self.buffer) < self.batch_size:
            return None

        obs, acoes, rewards, obs_next, dones, indices, weights = \
            self.buffer.sample(self.batch_size)

        obs_t      = torch.tensor(obs,      device=self.device)
        acoes_t    = torch.tensor(acoes,    device=self.device)
        rewards_t  = torch.tensor(rewards,  device=self.device)
        obs_next_t = torch.tensor(obs_next, device=self.device)
        dones_t    = torch.tensor(dones,    device=self.device)
        weights_t  = torch.tensor(weights,  device=self.device)

        # Q atual
        q_values = self.q_net(obs_t).gather(1, acoes_t.unsqueeze(1)).squeeze(1)

        # Q target (Double DQN)
        with torch.no_grad():
            melhores_acoes = self.q_net(obs_next_t).argmax(dim=1, keepdim=True)
            q_next  = self.q_target(obs_next_t).gather(1, melhores_acoes).squeeze(1)
            q_target = rewards_t + self.gamma * q_next * (1 - dones_t)

        td_errors = (q_values - q_target).detach().cpu().numpy()

        # Perda ponderada pelos IS weights
        loss = (weights_t * nn.functional.smooth_l1_loss(
            q_values, q_target, reduction="none"
        )).mean()

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.optimizer.step()

        self.buffer.update_priorities(indices, td_errors)

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
