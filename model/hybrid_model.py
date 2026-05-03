import logging
import os
import time

import numpy as np
import torch

from model.cnn import LunarCNN
from model.physics import features_subsolo

logger = logging.getLogger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "model/pesos.pth"

modelo = LunarCNN().to(DEVICE)

if os.path.exists(MODEL_PATH):
    try:
        modelo.load_state_dict(
            torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
        )
        logger.info("Modelo carregado com pesos treinados")
    except Exception as e:
        logger.warning("Erro ao carregar pesos: %s", e)
else:
    logger.warning("Nenhum modelo treinado encontrado — iniciando do zero")

modelo.eval()


# =========================
# PREPROCESSAMENTO
# =========================


def preprocessar_imagem(imagem):
    if imagem is None:
        imagem = np.zeros((32, 32), dtype=np.float32)

    imagem = np.array(imagem, dtype=np.float32)

    if imagem.max() > imagem.min():
        imagem = (imagem - imagem.min()) / (imagem.max() - imagem.min())

    if imagem.shape != (64, 64):
        if imagem.ndim != 2:
            side = max(1, int(np.sqrt(imagem.size)))
            imagem = imagem.flat[:side * side].reshape(side, side)

        t = torch.tensor(imagem).float().unsqueeze(0).unsqueeze(0)
        t = torch.nn.functional.interpolate(
            t, size=(64, 64), mode="bilinear", align_corners=False
        )
        return t.to(DEVICE)

    tensor = torch.tensor(imagem).unsqueeze(0).unsqueeze(0)
    return tensor.to(DEVICE)


# =========================
# FEATURES FISICAS
# =========================


def features_fisicas(insolacao, lat, temp_superficie=None):
    """
    Features normalizadas (5 dims):
    [insol_norm, lat_norm, sub_0.1m_norm, sub_0.5m_norm, sub_1.0m_norm]
    Subsolo derivado de temp_superficie via difusão térmica (Vasavada 2012).
    temp_superficie não entra no modelo diretamente — só para calcular o perfil.
    """
    insol_n = (insolacao or 0) / 1361.0
    lat_n   = (lat or 0) / 90.0

    if temp_superficie is not None:
        sub = features_subsolo(float(temp_superficie))  # (3,)
    else:
        sub = np.zeros(3, dtype=np.float32)

    return torch.tensor(
        [[insol_n, lat_n, sub[0], sub[1], sub[2]]],
        dtype=torch.float32,
    ).to(DEVICE)


# =========================
# INFERENCIA
# =========================


def modelo_hibrido(imagem, insolacao, temperatura=None, lat=0):
    x   = preprocessar_imagem(imagem)
    env = features_fisicas(insolacao, lat, temp_superficie=temperatura)

    with torch.no_grad():
        prob = modelo(x, env).item()

    return float(np.clip(prob, 0.0, 1.0))


def prever_com_incerteza(imagem, insolacao, temperatura=None, lat=0, n_passes=30):
    """
    Monte Carlo Dropout: N forward passes com dropout ativo.
    Retorna (media, variancia) — variancia alta = modelo incerto.
    Ref: Gal & Ghahramani (2016), Dropout as Bayesian Approximation.
    """
    x   = preprocessar_imagem(imagem)
    env = features_fisicas(insolacao, lat, temp_superficie=temperatura)

    # Ativa apenas Dropout — mantém BatchNorm em eval para batch=1
    modelo.train()
    for m in modelo.modules():
        if isinstance(m, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d)):
            m.eval()

    preds = []
    with torch.no_grad():
        for _ in range(n_passes):
            preds.append(modelo(x, env).item())
    modelo.eval()

    preds = np.array(preds, dtype=np.float32)
    return float(np.clip(preds.mean(), 0.0, 1.0)), float(preds.var())


# =========================
# TREINAMENTO
# =========================


def treinar_step(imagem, insolacao, lat, label, optimizer, loss_fn, temperatura=None):
    modelo.train()

    x = preprocessar_imagem(imagem)
    env = features_fisicas(insolacao, lat, temp_superficie=temperatura)
    label_t = torch.tensor([[label]], dtype=torch.float32).to(DEVICE)

    pred = modelo(x, env)
    loss = loss_fn(pred, label_t)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    modelo.eval()

    return loss.item()


# =========================
# SALVAR MODELO
# =========================


def salvar_modelo():
    torch.save(modelo.state_dict(), MODEL_PATH)
    logger.info("Modelo salvo em: %s", MODEL_PATH)


# =========================
# TEMPO LUNAR
# =========================


def tempo_lunar():
    ciclo = 29.5 * 24 * 3600
    return (time.time() % ciclo) / ciclo
