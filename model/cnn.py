import torch
import torch.nn as nn
import torch.nn.functional as F


# =========================
# 🧠 BLOCO CNN (VISÃO)
# =========================

class CNNEncoder(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),   # 64x64
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 32x32

            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 16x16

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 8x8
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 128),  # 64x64 -> 3x MaxPool2d(2) -> 8x8 -> 4096
            nn.ReLU(),
            nn.Dropout(0.3)
        )

    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x


# =========================
# 🌍 BLOCO FÍSICO (FEATURES)
# =========================

class PhysicsEncoder(nn.Module):
    def __init__(self, input_dim=5):
        """
        input_dim esperado (5 features):
        [insolacao_norm, lat_norm, sub_0.1m_norm, sub_0.5m_norm, sub_1.0m_norm]
        Subsolo derivado de difusão térmica (Vasavada 2012) — independente dos labels PSR.
        """
        super().__init__()

        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),

            nn.Linear(32, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),

            nn.Linear(64, 64),
            nn.ReLU()
        )

    def forward(self, x):
        return self.mlp(x)


# =========================
# 🔗 FUSÃO MULTIMODAL
# =========================

class FusionHead(nn.Module):
    def __init__(self):
        super().__init__()

        self.fc = nn.Sequential(
            nn.Linear(128 + 64, 128),
            nn.ReLU(),
            nn.Dropout(0.4),

            nn.Linear(128, 64),
            nn.ReLU(),

            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, img_feat, phys_feat):
        x = torch.cat([img_feat, phys_feat], dim=1)
        return self.fc(x)


# =========================
# 🚀 MODELO COMPLETO
# =========================

class LunarCNN(nn.Module):
    def __init__(self):
        super().__init__()

        self.cnn = CNNEncoder()
        self.physics = PhysicsEncoder()
        self.head = FusionHead()

    def forward(self, img, env=None):
        """
        img: tensor [B, 1, 64, 64]
        env: tensor [B, 5] -> (insolacao_norm, lat_norm, sub_0.1m, sub_0.5m, sub_1.0m)
        """
        img_feat = self.cnn(img)

        if env is None:
            env = torch.zeros((img.shape[0], 5), device=img.device)

        phys_feat = self.physics(env)
        out = self.head(img_feat, phys_feat)
        return out