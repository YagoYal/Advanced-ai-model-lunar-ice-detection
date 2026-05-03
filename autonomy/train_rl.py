"""
Treinamento DQN do rover lunar.

Uso:
    python -m autonomy.train_rl
    python -m autonomy.train_rl --episodios 2000 --passos 300
"""

import argparse
import os
import sys
import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomy.rl_env   import LunarRoverEnv
from autonomy.rl_agent import DQNAgent

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def carregar_mapas() -> tuple:
    insol_path = "data/processed/lro/insolacao.npy"
    label_path = "data/processed/lro/labels_gelo.npy"

    if not os.path.exists(insol_path) or not os.path.exists(label_path):
        print("Dados nao encontrados. Rodando gerador...")
        from data.data_pipeline.generate_scientific_data import gerar_dados
        from data.data_pipeline.generate_labels import salvar_labels
        gerar_dados("data/processed/lro/", modo="real", verbose=False)
        salvar_labels("data/processed/lro/", verbose=False)

    insolacao = np.load(insol_path)
    labels    = np.load(label_path)

    subsolo_path = "data/processed/lro/temperatura_subsolo.npy"
    subsolo = np.load(subsolo_path) if os.path.exists(subsolo_path) else None

    return insolacao, labels, subsolo


def treinar(episodios: int = 1000, max_passos: int = 200, verbose_a: int = 100):
    print(f"Treinamento RL | episodios={episodios} | device={DEVICE}")

    insolacao, labels, subsolo = carregar_mapas()

    env = LunarRoverEnv(
        insolacao_map=insolacao,
        label_map=labels,
        max_passos=max_passos,
        temp_subsolo_map=subsolo,
    )

    agente = DQNAgent(
        obs_dim=env.obs_dim,
        n_acoes=env.n_acoes,
        device=DEVICE,
        epsilon_decay=episodios * max_passos // 3,
    )

    historico = []
    melhor_ice = 0.0

    for ep in range(episodios):
        obs   = env.reset()
        ep_reward  = 0.0
        ep_loss    = []
        ice_max_ep = 0.0

        for _ in range(max_passos):
            acao = agente.selecionar_acao(obs)
            obs_next, reward, done, info = env.step(acao)

            agente.buffer.push(obs, acao, reward, obs_next, done)
            obs = obs_next

            loss = agente.treinar()
            if loss is not None:
                ep_loss.append(loss)

            agente.atualizar_target()

            ep_reward  += reward
            ice_max_ep  = max(ice_max_ep, info["ice_max"])

            if done:
                break

        historico.append({
            "ep": ep,
            "reward": ep_reward,
            "ice_max": ice_max_ep,
            "loss_media": np.mean(ep_loss) if ep_loss else 0,
            "epsilon": agente.epsilon,
        })

        if ice_max_ep > melhor_ice:
            melhor_ice = ice_max_ep
            agente.salvar("model/rl_pesos.pth")

        if (ep + 1) % verbose_a == 0:
            r_medio  = np.mean([h["reward"]  for h in historico[-verbose_a:]])
            ice_medio = np.mean([h["ice_max"] for h in historico[-verbose_a:]])
            loss_med = np.mean([h["loss_media"] for h in historico[-verbose_a:]])
            print(
                f"Ep {ep+1:4d}/{episodios} | "
                f"reward={r_medio:.2f}  ice_max={ice_medio:.3f}  "
                f"loss={loss_med:.4f}  eps={agente.epsilon:.3f}"
            )

    np.save("model/rl_historico.npy", np.array(historico, dtype=object))
    print(f"\nTreinamento RL concluido.")
    print(f"Melhor ice_max: {melhor_ice:.3f}")
    print(f"Modelo salvo: model/rl_pesos.pth")

    return historico


def demo_agente_treinado(passos: int = 50):
    """Roda o agente treinado e exibe o caminho."""
    if not os.path.exists("model/rl_pesos.pth"):
        print("Modelo RL nao encontrado. Rode train_rl.py primeiro.")
        return

    insolacao, labels, subsolo = carregar_mapas()
    env = LunarRoverEnv(insolacao_map=insolacao, label_map=labels, max_passos=passos, temp_subsolo_map=subsolo)

    agente = DQNAgent(obs_dim=env.obs_dim, n_acoes=env.n_acoes, device=DEVICE)
    agente.carregar("model/rl_pesos.pth")
    agente.epsilon = 0.0   # modo greedy puro

    obs = env.reset()
    print(f"Inicio: {env.render_pos()}\n")

    for passo in range(passos):
        acao = agente.selecionar_acao(obs)
        obs, reward, done, info = env.step(acao)
        dir_nome = env.nomes_acoes[acao]
        print(f"Passo {passo+1:3d} | {dir_nome} | {env.render_pos()} | reward={reward:.3f}")
        if done:
            break

    print(f"\nMelhor gelo encontrado: {info['ice_max']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodios", type=int, default=1000)
    parser.add_argument("--passos",    type=int, default=200)
    parser.add_argument("--demo",      action="store_true")
    args = parser.parse_args()

    if args.demo:
        demo_agente_treinado()
    else:
        treinar(episodios=args.episodios, max_passos=args.passos)
