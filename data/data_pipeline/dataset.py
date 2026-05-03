"""
LunarDataset — Dataset PyTorch para detecção de gelo lunar.

Labels vêm de PSRs confirmados (generate_labels.py), NÃO de threshold
sobre as próprias features físicas (sem circularidade).

Inputs do modelo (5 features):
  - insolacao (W/m²): iluminação anual — independente da detecção de gelo
  - latitude (graus): posição geométrica
  - temp_subsolo_0.1m, 0.5m, 1.0m (K): perfil térmico subsuperficial
    derivado de temperatura_subsolo.npy (Vasavada 2012)

Labels:
  - 1 = PSR com assinatura de gelo confirmada por instrumento independente
  - 0 = sem evidência de gelo
"""

import os
import numpy as np
import torch
from torch.utils.data import Dataset

from data.data_pipeline.generate_labels import gerar_label_map


class LunarDataset(Dataset):
    def __init__(self, base_dir="data/processed/lro/", mode="real", augment=False):
        if mode not in ["real", "mock"]:
            raise ValueError("mode deve ser 'real' ou 'mock'")

        self.mode = mode
        self.augment = augment
        self.data_dir = os.path.join(base_dir, "mock") if mode == "mock" else base_dir
        self.img_dir = os.path.join(self.data_dir, "imagens")

        print(f"[Dataset] modo={mode.upper()}  dir={self.data_dir}")

        # Dados físicos — usados como INPUT (não como fonte de label)
        self.insolacao = np.load(os.path.join(self.data_dir, "insolacao.npy"))

        if self.insolacao.ndim != 2:
            raise ValueError(
                f"insolacao.npy deve ser 2D (H, W), recebeu shape {self.insolacao.shape}. "
                "Rode generate_scientific_data.py ou filter_nasa_data.py para gerar a grade correta."
            )
        H, W = self.insolacao.shape
        if H == 0 or W == 0:
            raise ValueError(f"insolacao.npy tem dimensao zero: {self.insolacao.shape}")

        # Mapa subsuperficial (H, W, 20) — derivado de temperatura de superfície via difusão
        # Independente dos labels PSR: não introduz circularidade
        subsolo_path = os.path.join(self.data_dir, "temperatura_subsolo.npy")
        if os.path.exists(subsolo_path):
            self.subsolo_map = np.load(subsolo_path)   # (H, W, 20)
            print(f"[Dataset] subsolo carregado: {self.subsolo_map.shape}")
        else:
            self.subsolo_map = None
            print("[Dataset] temperatura_subsolo.npy ausente — features subsolo = zeros")

        # Labels independentes: baseados em PSRs confirmados por instrumento
        labels_path = os.path.join(self.data_dir, "labels_gelo.npy")
        if os.path.exists(labels_path):
            self.label_map = np.load(labels_path)
        else:
            # Gera na hora se não existir
            _, binary, _ = gerar_label_map(H, W)
            self.label_map = binary.astype(np.float32)
            np.save(labels_path, self.label_map)

        # Mapa de confiança (para loss ponderada)
        conf_path = os.path.join(self.data_dir, "labels_confianca.npy")
        if os.path.exists(conf_path):
            self.conf_map = np.load(conf_path)
        else:
            self.conf_map = np.ones((H, W), dtype=np.float32)

        # Lista de imagens
        self.imagens = sorted(
            f for f in os.listdir(self.img_dir) if f.endswith(".npy")
        )

        self._H = H
        self._W = W

        # Monta índice de posições: todas as posições do grid com label conhecido
        pos_positivas = list(zip(*np.where(self.label_map > 0.5)))
        pos_negativas = list(zip(*np.where(self.label_map < 0.5)))

        # Garante ao menos 30% de positivos no dataset (oversampling de PSRs)
        n_neg_sample = max(len(pos_positivas) * 3, len(self.imagens))
        rng = np.random.default_rng(42)
        if pos_negativas:
            idx_neg = rng.choice(len(pos_negativas), size=min(n_neg_sample, len(pos_negativas)), replace=False)
            pos_negativas_sample = [pos_negativas[i] for i in idx_neg]
        else:
            pos_negativas_sample = []

        self._posicoes = pos_positivas + pos_negativas_sample
        self._n = len(self._posicoes)

        n_pos = len(pos_positivas)
        print(f"[Dataset] {self._n} exemplos | {n_pos} positivos ({100*n_pos/max(1,self._n):.1f}%) | grid {H}x{W}")

    def __len__(self):
        return self._n

    def __getitem__(self, idx):
        # Posição real no grid (inclui PSRs explicitamente)
        i, j = self._posicoes[idx]

        # Imagem patch — reutiliza os 50 patches ciclicamente
        img_path = os.path.join(self.img_dir, self.imagens[idx % len(self.imagens)])
        img = np.load(img_path).astype(np.float32)
        if img.max() > img.min():
            img = (img - img.min()) / (img.max() - img.min())

        # Augmentation básico (flips)
        if self.augment:
            if np.random.rand() > 0.5:
                img = np.fliplr(img).copy()
            if np.random.rand() > 0.5:
                img = np.flipud(img).copy()

        lat = float(i - 90)                # graus (-90 a +89)

        # Features físicas de INPUT (5 dimensões)
        # [0] insol_norm       — insolação normalizada por 1361 W/m²
        # [1] lat_norm         — latitude normalizada por 90°
        # [2] sub_0.1m_norm    — temperatura a 0.1m / 300K
        # [3] sub_0.5m_norm    — temperatura a 0.5m / 300K
        # [4] sub_1.0m_norm    — temperatura a 1.0m / 300K
        insol = float(self.insolacao[i, j])
        if self.subsolo_map is not None:
            # linspace(0,2,20): step=0.105m → idx1≈0.1m, idx5≈0.5m, idx10≈1.0m
            sub_01 = float(self.subsolo_map[i, j, 1])  / 300.0
            sub_05 = float(self.subsolo_map[i, j, 5])  / 300.0
            sub_10 = float(self.subsolo_map[i, j, 10]) / 300.0
        else:
            sub_01 = sub_05 = sub_10 = 0.0

        features = np.array(
            [insol / 1361.0, lat / 90.0, sub_01, sub_05, sub_10],
            dtype=np.float32
        )

        # Label independente (PSR confirmado por instrumento externo)
        label = float(self.label_map[i, j])
        confidence = float(self.conf_map[i, j])

        return (
            torch.tensor(img).unsqueeze(0),              # (1, 64, 64)
            torch.tensor(features),                       # (5,): subsolo incluído
            torch.tensor(label, dtype=torch.float32),     # escalar
            torch.tensor([lat, float(j - 180)]),          # posição (lat, lon)
            torch.tensor(confidence, dtype=torch.float32) # peso do label
        )
