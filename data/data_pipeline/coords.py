"""
Utilitários de coordenadas — ponto único de verdade para todo o projeto.

Sistema de referência:
  Grade interna : (i, j) onde i=0..179, j=0..359
  Graus         : lat = i - 90  (-90 a +89)
                  lon = j - 180 (-180 a +179)
  Normalizado   : lat_n = lat / 90   (-1 a +1)
                  lon_n = lon / 180  (-1 a +1)
"""

import numpy as np


# ─── Grade → Graus ────────────────────────────────────────────────────────────

def grid_para_graus(i: int, j: int) -> tuple[float, float]:
    return float(i - 90), float(j - 180)


def graus_para_grid(lat: float, lon: float, H: int = 180, W: int = 360) -> tuple[int, int]:
    i = int(round(lat + 90))
    j = int(round(lon + 180))
    return max(0, min(H - 1, i)), max(0, min(W - 1, j))


# ─── Frontend (Leaflet) → Grade ───────────────────────────────────────────────

def leaflet_para_grid(lat_deg: float, lon_deg: float) -> tuple[int, int]:
    """Coordenadas Leaflet (graus decimais) para índice de grade."""
    return graus_para_grid(lat_deg, lon_deg)


def grid_para_leaflet(i: int, j: int) -> tuple[float, float]:
    """Índice de grade para coordenadas Leaflet."""
    return grid_para_graus(i, j)


# ─── Normalização para modelo ──────────────────────────────────────────────────

def normalizar_features(insolacao: float, lat_graus: float,
                        temp_superficie: float = None) -> np.ndarray:
    """
    Features normalizadas para o modelo CNN (5 dims):
    [insol_norm, lat_norm, sub_0.1m_norm, sub_0.5m_norm, sub_1.0m_norm]
    temp_superficie usada para derivar perfil subsolo via physics.features_subsolo().
    """
    from model.physics import features_subsolo
    insol_n = insolacao / 1361.0
    lat_n   = lat_graus / 90.0
    sub     = features_subsolo(float(temp_superficie)) if temp_superficie is not None \
              else np.zeros(3, dtype=np.float32)
    return np.array([insol_n, lat_n, sub[0], sub[1], sub[2]], dtype=np.float32)


# ─── Pixel de imagem remota → Grade ───────────────────────────────────────────

def lroc_pixel_para_grid(row: int, col: int,
                          img_h: int = 54582, img_w: int = 109164) -> tuple[int, int]:
    """Pixel do LROC WAC global mosaic (54582×109164) para grade 180×360."""
    lat = 90 - (row / img_h) * 180
    lon = (col / img_w) * 360 - 180
    return graus_para_grid(lat, lon)


def mini_rf_row_para_lat(row: int, total_rows: int, lat_start: float, lat_end: float) -> float:
    """Linha do Mini-RF (faixa polar) para latitude em graus."""
    return lat_start + (row / total_rows) * (lat_end - lat_start)


# ─── Distância angular ────────────────────────────────────────────────────────

def distancia_angular(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância euclidiana em graus (aproximação válida em regiões pequenas)."""
    return float(np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2))
