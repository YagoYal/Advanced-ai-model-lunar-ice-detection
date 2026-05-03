import logging
import os

import numpy as np

logger = logging.getLogger(__name__)


class AmbienteLunar:
    """
    Ambiente lunar com acesso O(1) por indexação numpy.

    Aceita arrays 2-D (H×W) para temperatura e insolação.
    Mantém retro-compatibilidade com dicts via conversão automática.
    """

    def __init__(
        self,
        mapa_imagens=None,
        mapa_insolacao=None,
        mapa_temperatura=None,
        arr_insolacao: np.ndarray | None = None,
        arr_temperatura: np.ndarray | None = None,
        arr_temp_subsolo: np.ndarray | None = None,
        img_dir: str = "",
        n_imgs: int = 0,
    ):
        # Modo array (preferido): acesso O(1) sem dicts
        self._arr_insol   = arr_insolacao
        self._arr_temp    = arr_temperatura
        self._arr_subsolo = arr_temp_subsolo   # (H, W, 20) ou None
        self._img_dir     = img_dir
        self._n_imgs      = n_imgs

        # Modo legado: dicts (mantido para compatibilidade)
        self.mapa_imagens     = mapa_imagens     or {}
        self.mapa_insolacao   = mapa_insolacao   or {}
        self.mapa_temperatura = mapa_temperatura or {}

        self.cache_imagens = {}

    def _caminho_img(self, lat: int, lon: int) -> str | None:
        if self._arr_insol is not None and self._n_imgs > 0:
            W = self._arr_insol.shape[1]
            nome = f"img_{(lat * W + lon) % self._n_imgs:03d}.npy"
            p = os.path.join(self._img_dir, nome)
            return p if os.path.exists(p) else None
        return self.mapa_imagens.get((lat, lon))

    def _insolacao(self, lat: int, lon: int) -> float:
        if self._arr_insol is not None:
            return float(self._arr_insol[int(lat), int(lon)])
        return self.mapa_insolacao.get((lat, lon), 500.0)

    def _temperatura(self, lat: int, lon: int) -> float:
        if self._arr_temp is not None:
            return float(self._arr_temp[int(lat), int(lon)])
        return self.mapa_temperatura.get((lat, lon), 200.0)

    def get_dados(self, pos):
        lat, lon = int(pos[0]), int(pos[1])
        # Garante que índices estejam dentro dos bounds — evita wrap silencioso do numpy
        if self._arr_insol is not None:
            lat = max(0, min(lat, self._arr_insol.shape[0] - 1))
            lon = max(0, min(lon, self._arr_insol.shape[1] - 1))
        caminho = self._caminho_img(lat, lon)

        if caminho in self.cache_imagens:
            imagem = self.cache_imagens[caminho]
        elif caminho and os.path.exists(caminho):
            raw = np.load(caminho).astype(np.float32)
            if raw.max() > raw.min():
                raw = (raw - raw.min()) / (raw.max() - raw.min())
            self.cache_imagens[caminho] = raw
            imagem = raw
        else:
            rng = np.random.default_rng(int(abs(lat * 1000 + lon)))
            imagem = rng.random((64, 64)).astype(np.float32)

        return imagem, self._insolacao(lat, lon)

    def _temp_subsolo(self, lat: int, lon: int) -> np.ndarray | None:
        """Retorna perfil subsuperficial (20,) em K, ou None se indisponível."""
        if self._arr_subsolo is not None:
            return self._arr_subsolo[int(lat), int(lon)]   # (20,)
        return None

    def get_dados_completo(self, pos):
        imagem, insolacao = self.get_dados(pos)
        lat, lon = int(pos[0]), int(pos[1])
        return imagem, insolacao, self._temperatura(lat, lon)

    def get_dados_subsolo(self, pos):
        """Retorna (imagem, insolacao, temperatura, perfil_subsolo_20camadas)."""
        imagem, insolacao = self.get_dados(pos)
        lat, lon = pos
        return imagem, insolacao, self._temperatura(lat, lon), self._temp_subsolo(lat, lon)

    def get_custo(self, pos):
        imagem, insolacao = self.get_dados(pos)
        custo_energia = 1.0 / (insolacao + 1e-5)
        risco = float(np.mean(imagem))
        return custo_energia + risco
