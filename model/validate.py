"""
Validação científica do modelo LunarCNN.

Testa de forma independente:
  1. Cabeus (85.3°S, 35.5°W) — único PSR com gelo 100% confirmado (LCROSS 2009)
     deve retornar probabilidade ALTA
  2. Equador (0°, 0°) — sem gelo, deve retornar probabilidade BAIXA
  3. Hermite (86.1°N, 89.9°W) — PSR mais frio medido (26K), deve ser ALTO
  4. Tycho crater (-43°, -11°) — não-PSR em mid-latitude, deve ser BAIXO

Interpretação dos resultados:
  - Se Cabeus > 0.6 e Equador < 0.3 → modelo aprendeu algo real
  - Se todos os valores estão perto de 0.5 → modelo não treinou / aleatorio
"""

import os
import sys
import torch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model.cnn import LunarCNN
from autonomy.environment import AmbienteLunar
from model.physics import features_subsolo

WEIGHTS_PATH = "model/pesos.pth"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Casos de teste: (nome, lat_deg, lon_deg, esperado)
CASOS_VALIDACAO = [
    ("Cabeus (LCROSS gelo confirmado)",   -85.32, -35.50, "ALTO"),
    ("Shackleton (LAMP assinatura UV)",   -89.90,   0.00, "ALTO"),
    ("Hermite (26K mais frio medido)",     86.10, -89.90, "ALTO"),
    ("Equador centro",                      0.00,   0.00, "BAIXO"),
    ("Mare Tranquillitatis (Apollo 11)",    0.67,  23.47, "BAIXO"),
    ("Tycho crater (mid-lat nao-PSR)",    -43.30, -11.20, "BAIXO"),
]


def lat_lon_para_grid(lat: float, lon: float, H: int = 180, W: int = 360):
    i = int(round(lat + 90))
    j = int(round(lon + 180))
    return max(0, min(H - 1, i)), max(0, min(W - 1, j))


_IMG_DIR = "data/processed/lro/imagens"
_IMG_FILES: list = []


def _carregar_patch(i: int, j: int, W: int = 360) -> np.ndarray:
    """Retorna patch real do disco (ciclico por posicao) ou zeros como fallback."""
    global _IMG_FILES
    if not _IMG_FILES and os.path.isdir(_IMG_DIR):
        _IMG_FILES = sorted(f for f in os.listdir(_IMG_DIR) if f.endswith(".npy"))
    if _IMG_FILES:
        nome = _IMG_FILES[(i * W + j) % len(_IMG_FILES)]
        patch = np.load(os.path.join(_IMG_DIR, nome)).astype(np.float32)
        if patch.max() > patch.min():
            patch = (patch - patch.min()) / (patch.max() - patch.min())
        return patch
    return np.zeros((64, 64), dtype=np.float32)


def preparar_input(insol_norm: float, lat_norm: float, i: int = 0, j: int = 0,
                   temp_superficie: float = None) -> tuple:
    """Cria tensores de entrada (5 features) para o modelo com patch real quando disponivel."""
    img = _carregar_patch(i, j)

    if temp_superficie is not None:
        sub = features_subsolo(temp_superficie)   # (3,)
    else:
        sub = np.zeros(3, dtype=np.float32)

    features = np.array(
        [insol_norm, lat_norm, sub[0], sub[1], sub[2]],
        dtype=np.float32
    )

    img_t  = torch.tensor(img).unsqueeze(0).unsqueeze(0).to(DEVICE)
    feat_t = torch.tensor(features).unsqueeze(0).to(DEVICE)
    return img_t, feat_t


def rodar_validacao(insolacao_map: np.ndarray = None) -> list:
    if not os.path.exists(WEIGHTS_PATH):
        print(f"Modelo nao encontrado: {WEIGHTS_PATH}")
        print("Rode: python -m model.train")
        return []

    model = LunarCNN().to(DEVICE)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=DEVICE, weights_only=True))
    model.eval()
    print(f"Modelo carregado: {WEIGHTS_PATH}\n")

    # Carrega mapas de insolação e temperatura
    if insolacao_map is None:
        insol_path = "data/processed/lro/insolacao.npy"
        insolacao_map = np.load(insol_path) if os.path.exists(insol_path) else np.ones((180, 360)) * 500.0

    temp_path = "data/processed/lro/temperatura.npy"
    temperatura_map = np.load(temp_path) if os.path.exists(temp_path) else None

    resultados = []
    print(f"{'Caso':<42} {'Prob':>6}  {'Esperado':>7}  {'OK':>3}")
    print("-" * 65)

    for nome, lat, lon, esperado in CASOS_VALIDACAO:
        i, j = lat_lon_para_grid(lat, lon)
        insol      = float(insolacao_map[i, j])
        insol_norm = insol / 1361.0
        lat_norm   = lat  / 90.0
        temp_sup   = float(temperatura_map[i, j]) if temperatura_map is not None else None

        img_t, feat_t = preparar_input(insol_norm, lat_norm, i, j, temp_superficie=temp_sup)

        with torch.no_grad():
            prob = model(img_t, feat_t).item()

        ok = ("ALTO"  if prob > 0.5 else "BAIXO") == esperado
        simbolo = "OK" if ok else "!!"
        print(f"{nome:<42} {prob:>6.3f}  {esperado:>7}  {simbolo:>3}")

        resultados.append({
            "caso": nome, "lat": lat, "lon": lon,
            "prob": prob, "esperado": esperado, "correto": ok,
        })

    n_corretos = sum(r["correto"] for r in resultados)
    print(f"\nResultado: {n_corretos}/{len(resultados)} casos corretos")

    if n_corretos == len(resultados):
        print("Modelo passou em todos os casos de validacao cientifica.")
    elif n_corretos >= len(resultados) // 2:
        print("Modelo parcialmente correto — continue treinando.")
    else:
        print("Modelo aleatorio ou mal treinado — verifique labels e epochs.")

    return resultados


if __name__ == "__main__":
    rodar_validacao()
