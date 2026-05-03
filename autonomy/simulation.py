"""
Simulação local de rover lunar com dados reais carregados do pipeline.
Útil para testar o planner sem subir o backend.

Uso:
    python -m autonomy.simulation
    python -m autonomy.simulation --passos 50 --lat 5 --lon 180
"""

import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomy.rover import Rover
from autonomy.environment import AmbienteLunar
from autonomy.planner import Planner


def carregar_ambiente(data_dir: str = "data/processed/lro/") -> AmbienteLunar:
    """Carrega ambiente com dados reais do pipeline — acesso O(1) via arrays numpy."""
    temp_path  = os.path.join(data_dir, "temperatura.npy")
    insol_path = os.path.join(data_dir, "insolacao.npy")
    img_dir    = os.path.join(data_dir, "imagens")

    if not os.path.exists(temp_path):
        print(f"Dados nao encontrados em {data_dir}. Rode: make data")
        sys.exit(1)

    temp  = np.load(temp_path).astype(np.float32)
    insol = np.load(insol_path).astype(np.float32)
    n_imgs = len([f for f in os.listdir(img_dir) if f.endswith(".npy")]) if os.path.isdir(img_dir) else 0

    subsolo_path = os.path.join(data_dir, "temperatura_subsolo.npy")
    subsolo = np.load(subsolo_path).astype(np.float32) if os.path.exists(subsolo_path) else None

    return AmbienteLunar(
        arr_insolacao=insol,
        arr_temperatura=temp,
        arr_temp_subsolo=subsolo,
        img_dir=img_dir,
        n_imgs=n_imgs,
    )


def rodar_simulacao(pos_inicial: list, passos: int = 20, data_dir: str = "data/processed/lro/"):
    print(f"Carregando ambiente de {data_dir}...")
    ambiente = carregar_ambiente(data_dir)

    rover   = Rover(pos_inicial, energia=100)
    planner = Planner(rover, ambiente)

    lat_ini = pos_inicial[0] - 90
    lon_ini = pos_inicial[1] - 180
    print(f"Inicio: grid={pos_inicial}  lat={lat_ini:+d}  lon={lon_ini:+d}\n")

    for i in range(passos):
        if rover.energia <= 0:
            print("Energia esgotada.")
            break

        mov = planner.passo()
        pos = rover.get_pos()
        lat = pos[0] - 90
        lon = pos[1] - 180

        _, insol, temp = ambiente.get_dados_completo(tuple(pos))
        print(
            f"Passo {i+1:3d} | {mov} -> grid={pos}  lat={lat:+d} lon={lon:+d} "
            f"| T={temp:.1f}  insol={insol:.1f}  energia={rover.energia:.1f}"
        )

    print("\nSimulacao concluida.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--passos", type=int, default=20)
    parser.add_argument("--lat",    type=int, default=5,   help="Indice de latitude (0-179)")
    parser.add_argument("--lon",    type=int, default=180, help="Indice de longitude (0-359)")
    parser.add_argument("--mock",   action="store_true",   help="Usa dados mock (mais rapido)")
    args = parser.parse_args()

    data_dir = "data/processed/lro/mock/" if args.mock else "data/processed/lro/"
    rodar_simulacao([args.lat, args.lon], passos=args.passos, data_dir=data_dir)
