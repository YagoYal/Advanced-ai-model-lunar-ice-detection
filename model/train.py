"""
Treinamento do LunarCNN para detecção de gelo.

Correções em relação à versão anterior:
  - Unpack correto: 5 valores do dataset (img, features, label, pos, conf)
  - Labels PSR-based (independentes dos inputs — sem circularidade)
  - Weighted BCE loss (dataset muito desbalanceado: ~4% positivos)
  - Salva o MELHOR modelo por val_loss, não o último
  - Métricas: loss, accuracy, precision, recall, F1
"""

import os
import sys
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.data_pipeline.dataset import LunarDataset
from model.cnn import LunarCNN

# ─── Config ───────────────────────────────────────────────────────────────────
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EPOCHS     = int(os.getenv("TRAIN_EPOCHS", 30))
LR         = 1e-3
BATCH_SIZE = 16
MODE       = os.getenv("DATA_MODE", "real")
WEIGHTS_PATH = "model/pesos.pth"

# Limita VRAM a 70% para não saturar a GPU (deixa margem para OS e outros processos)
if DEVICE.type == "cuda":
    torch.cuda.set_per_process_memory_fraction(0.7)
    print(f"GPU: {torch.cuda.get_device_name(0)} | VRAM limitada a 70%")

print(f"Device: {DEVICE} | Modo: {MODE} | Epochs: {EPOCHS}")


# ─── Dataset e splits ─────────────────────────────────────────────────────────
dataset = LunarDataset(mode=MODE, augment=True)

n = len(dataset)
n_train = int(0.8 * n)
n_val   = n - n_train
train_ds, val_ds = random_split(dataset, [n_train, n_val])

labels_all = np.array([dataset[i][2].item() for i in range(n)])
n_pos = int(labels_all.sum())
n_neg = n - n_pos

_pm = DEVICE.type == "cuda"

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, pin_memory=_pm)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, pin_memory=_pm)

print(f"Train: {n_train} | Val: {n_val} | Pos: {n_pos} ({100*n_pos/n:.1f}%)")


# ─── Modelo ───────────────────────────────────────────────────────────────────
model = LunarCNN().to(DEVICE)

# BCE ponderada: pos_weight=n_neg/n_pos compensa 3:1 sem risco de saturação focal
_pos_w = torch.tensor([n_neg / (n_pos + 1e-9)], device=DEVICE)

def criterion(pred, target):
    w = torch.where(target == 1, _pos_w.expand_as(target), torch.ones_like(target))
    return nn.functional.binary_cross_entropy(pred.clamp(1e-7, 1-1e-7), target, weight=w)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)


# ─── Métricas ─────────────────────────────────────────────────────────────────
def calcular_metricas(preds: torch.Tensor, labels: torch.Tensor) -> dict:
    pred_bin = (preds > 0.5).float()
    tp = ((pred_bin == 1) & (labels == 1)).sum().float()
    fp = ((pred_bin == 1) & (labels == 0)).sum().float()
    fn = ((pred_bin == 0) & (labels == 1)).sum().float()
    tn = ((pred_bin == 0) & (labels == 0)).sum().float()

    acc       = (tp + tn) / (tp + fp + fn + tn + 1e-9)
    precision = tp / (tp + fp + 1e-9)
    recall    = tp / (tp + fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)

    return {
        "acc": acc.item(), "precision": precision.item(),
        "recall": recall.item(), "f1": f1.item(),
    }


# ─── Validação ────────────────────────────────────────────────────────────────
def avaliar(loader) -> tuple:
    model.eval()
    total_loss = 0.0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for img, features, label, pos, conf in loader:
            img     = img.to(DEVICE)
            features = features.to(DEVICE)
            label   = label.to(DEVICE).unsqueeze(1)

            pred = model(img, features)
            loss = criterion(pred, label)
            total_loss += loss.item()

            all_preds.append(pred.squeeze(1))
            all_labels.append(label.squeeze(1))

    preds_t  = torch.cat(all_preds)
    labels_t = torch.cat(all_labels)
    metricas = calcular_metricas(preds_t, labels_t)
    return total_loss / len(loader), metricas


# ─── Loop de treino ───────────────────────────────────────────────────────────
melhor_val_loss = float("inf")
historico = []

for epoch in range(EPOCHS):
    model.train()
    train_loss = 0.0

    for img, features, label, pos, conf in train_loader:
        img      = img.to(DEVICE)
        features = features.to(DEVICE)
        label    = label.to(DEVICE).unsqueeze(1)

        pred = model(img, features)
        loss = criterion(pred, label)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        train_loss += loss.item()

    scheduler.step()

    val_loss, metricas = avaliar(val_loader)
    train_loss /= len(train_loader)

    historico.append({
        "epoch": epoch,
        "train_loss": train_loss,
        "val_loss": val_loss,
        **metricas,
    })

    print(
        f"Epoch {epoch:02d} | "
        f"train={train_loss:.4f}  val={val_loss:.4f} | "
        f"acc={metricas['acc']:.3f}  prec={metricas['precision']:.3f}  "
        f"rec={metricas['recall']:.3f}  F1={metricas['f1']:.3f}"
    )

    # Salva melhor modelo por val_loss
    if val_loss < melhor_val_loss:
        melhor_val_loss = val_loss
        torch.save(model.state_dict(), WEIGHTS_PATH)
        print(f"  -> Melhor modelo salvo (val_loss={val_loss:.4f})")

# Salva histórico
np.save("model/historico_treino.npy", np.array(historico, dtype=object))
print(f"\nTreinamento concluido. Melhor val_loss: {melhor_val_loss:.4f}")
print(f"Modelo salvo em: {WEIGHTS_PATH}")
