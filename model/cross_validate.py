"""
P7 — Cross-validation por quadrante polar.

Pergunta científica: o LunarCNN generaliza física real (insolação, perfil
térmico subsuperficial) para uma região polar nunca vista, ou está apenas
memorizando os PSRs específicos do treino?

Método (2 experimentos independentes, pesos descartáveis — nunca sobrescreve
model/pesos.pth, o modelo de produção):

  1. hold_sul:   treina SEM nenhum exemplo com lat <= -60° (quadrante polar
                 sul inteiro fora do treino) → valida só nesse quadrante.
  2. hold_norte: mesma lógica espelhada para lat >= +60°.

|lat| > 60° é o mesmo limiar de "região polar" já usado em
`generate_scientific_data.py` (mask_hi/mask_p/mask_dp/mask_xp) — reaproveita
a convenção existente do projeto em vez de inventar um novo threshold.

lat_norm é uma das 5 features de input do modelo — então o quadrante
retido fica com valores de latitude que o modelo nunca viu durante o
treino (não é só "PSR novo", é "faixa de lat_norm nunca vista"). Teste
propositalmente mais rígido que um cross-validation aleatório comum.

Uso:
    python -m model.cross_validate                  # 30 épocas por fold (padrão)
    CV_EPOCHS=10 python -m model.cross_validate      # mais rápido p/ checagem

Mitigação (2026-08-20): hipótese confirmada — lat_norm (feature [1] de 5)
funcionava como atalho de lookup, o modelo memorizava "essa faixa de latitude
é polo" em vez de aprender a relação física insolação/perfil térmico → gelo.
Testado zerando lat_norm (treino e validação) e comparando: F1 0.000→0.808
(hold_sul), 0.731 instável→0.767 estável (hold_norte) — números variam
±0.01 entre retreinos (inicialização/split aleatórios), não são bit-exact.
**A mitigação virou o
padrão de produção** — `data/data_pipeline/dataset.py` já zera lat_norm
sempre, então rodar este script sem flag nenhuma já reflete o modelo real.
CV_ABLATE_LAT=1 fica só como registro histórico do experimento A/B original
(hoje é redundante — zera uma coluna que o dataset já zera):

    python -m model.cross_validate                  # produção atual (lat_norm já zerada por padrão)
    CV_ABLATE_LAT=1 python -m model.cross_validate   # idêntico ao acima, mantido por histórico

Saída:
    model/cross_validation/pesos_hold_sul[_ablate_lat].pth
    model/cross_validation/pesos_hold_norte[_ablate_lat].pth
    model/cross_validation/results[_ablate_lat].json
"""

import json
import os
import sys

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.data_pipeline.dataset import LunarDataset
from model.cnn import LunarCNN

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EPOCHS = int(os.getenv("CV_EPOCHS", 30))
LR = 1e-3
BATCH_SIZE = 16
MODE = os.getenv("DATA_MODE", "real")
POLAR_THRESHOLD = 60.0  # graus — mesma convenção de generate_scientific_data.py
OUT_DIR = "model/cross_validation"
ABLATE_LAT = os.getenv("CV_ABLATE_LAT", "0") == "1"
LAT_FEATURE_IDX = 1  # ver data/data_pipeline/dataset.py — ordem das 5 features
SUFFIX = "_ablate_lat" if ABLATE_LAT else ""

if DEVICE.type == "cuda":
    torch.cuda.set_per_process_memory_fraction(0.7)


def calcular_metricas(preds: torch.Tensor, labels: torch.Tensor) -> dict:
    pred_bin = (preds > 0.5).float()
    tp = ((pred_bin == 1) & (labels > 0)).sum().float()
    fp = ((pred_bin == 1) & (labels == 0)).sum().float()
    fn = ((pred_bin == 0) & (labels > 0)).sum().float()
    tn = ((pred_bin == 0) & (labels == 0)).sum().float()

    acc = (tp + tn) / (tp + fp + fn + tn + 1e-9)
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)

    return {
        "acc": acc.item(), "precision": precision.item(),
        "recall": recall.item(), "f1": f1.item(),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
    }


def _ablate(features: torch.Tensor) -> torch.Tensor:
    """Zera lat_norm (feature [1]) se CV_ABLATE_LAT=1 — testa se o modelo
    generaliza pro quadrante retido usando só insolação/temperatura
    subsuperficial, sem a latitude como atalho direto."""
    if ABLATE_LAT:
        features = features.clone()
        features[:, LAT_FEATURE_IDX] = 0.0
    return features


def avaliar(model, loader, criterion) -> tuple:
    model.eval()
    total_loss = 0.0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for img, features, label, pos, conf in loader:
            img, features = img.to(DEVICE), _ablate(features).to(DEVICE)
            label = label.to(DEVICE).unsqueeze(1)
            pred = model(img, features)
            total_loss += criterion(pred, label).item()
            all_preds.append(pred.squeeze(1))
            all_labels.append(label.squeeze(1))
    preds_t = torch.cat(all_preds)
    labels_t = torch.cat(all_labels)
    return total_loss / len(loader), calcular_metricas(preds_t, labels_t)


def treinar_fold(nome: str, dataset: LunarDataset, train_idx: list, val_idx: list) -> dict:
    print(f"\n{'='*70}\nFOLD: {nome}\n{'='*70}")

    train_ds = Subset(dataset, train_idx)
    val_ds = Subset(dataset, val_idx)

    labels_train = np.array([dataset.label_map[dataset._posicoes[i]] for i in train_idx])
    labels_val = np.array([dataset.label_map[dataset._posicoes[i]] for i in val_idx])
    n_pos_train = int((labels_train > 0).sum())
    n_neg_train = len(train_idx) - n_pos_train
    n_pos_val = int((labels_val > 0).sum())

    print(f"Train: {len(train_idx)} ({n_pos_train} pos, {100*n_pos_train/len(train_idx):.1f}%) | "
          f"Val (quadrante retido): {len(val_idx)} ({n_pos_val} pos, "
          f"{100*n_pos_val/max(1,len(val_idx)):.1f}%)")

    if n_pos_val == 0:
        print("AVISO: quadrante retido não tem nenhum positivo — F1 não é interpretável.")
    if n_pos_train == 0:
        raise RuntimeError(f"Fold {nome}: zero positivos no treino — não há como aprender.")

    _pm = DEVICE.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, pin_memory=_pm)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, pin_memory=_pm)

    model = LunarCNN().to(DEVICE)
    pos_w = torch.tensor([n_neg_train / (n_pos_train + 1e-9)], device=DEVICE)

    def criterion(pred, target):
        w = torch.where(target > 0, pos_w.expand_as(target), torch.ones_like(target))
        return nn.functional.binary_cross_entropy(pred.clamp(1e-7, 1 - 1e-7), target, weight=w)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    melhor_val_loss = float("inf")
    melhor_metricas = None
    weights_path = os.path.join(OUT_DIR, f"pesos_{nome}{SUFFIX}.pth")

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for img, features, label, pos, conf in train_loader:
            img, features = img.to(DEVICE), _ablate(features).to(DEVICE)
            label = label.to(DEVICE).unsqueeze(1)
            pred = model(img, features)
            loss = criterion(pred, label)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        val_loss, metricas = avaliar(model, val_loader, criterion)
        train_loss /= len(train_loader)

        print(f"  epoch {epoch:02d} | train={train_loss:.4f} val={val_loss:.4f} | "
              f"F1_quadrante_retido={metricas['f1']:.3f} recall={metricas['recall']:.3f}")

        if val_loss < melhor_val_loss:
            melhor_val_loss = val_loss
            melhor_metricas = metricas
            torch.save(model.state_dict(), weights_path)

    return {
        "fold": nome,
        "n_train": len(train_idx), "n_pos_train": n_pos_train,
        "n_val": len(val_idx), "n_pos_val": n_pos_val,
        "melhor_val_loss": melhor_val_loss,
        "metricas_quadrante_retido": melhor_metricas,
        "weights_path": weights_path,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Device: {DEVICE} | Modo: {MODE} | Epochs/fold: {EPOCHS} | Limiar polar: {POLAR_THRESHOLD}° | "
          f"Ablate lat_norm: {ABLATE_LAT}")

    dataset = LunarDataset(mode=MODE, augment=False)
    lats = np.array([dataset._posicoes[i][0] - 90 for i in range(len(dataset))])

    idx_hold_sul_train = list(np.where(lats > -POLAR_THRESHOLD)[0])
    idx_hold_sul_val = list(np.where(lats <= -POLAR_THRESHOLD)[0])

    idx_hold_norte_train = list(np.where(lats < POLAR_THRESHOLD)[0])
    idx_hold_norte_val = list(np.where(lats >= POLAR_THRESHOLD)[0])

    resultados = [
        treinar_fold("hold_sul", dataset, idx_hold_sul_train, idx_hold_sul_val),
        treinar_fold("hold_norte", dataset, idx_hold_norte_train, idx_hold_norte_val),
    ]

    print(f"\n{'='*70}\nRESUMO P7 — cross-validation por quadrante polar\n{'='*70}")
    for r in resultados:
        m = r["metricas_quadrante_retido"]
        print(f"{r['fold']:12s} | quadrante nunca visto no treino: "
              f"F1={m['f1']:.3f} recall={m['recall']:.3f} precision={m['precision']:.3f} "
              f"acc={m['acc']:.3f} (n_val={r['n_val']}, n_pos_val={r['n_pos_val']})")

    out_path = os.path.join(OUT_DIR, f"results{SUFFIX}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "polar_threshold_deg": POLAR_THRESHOLD,
            "epochs_per_fold": EPOCHS,
            "ablate_lat_norm": ABLATE_LAT,
            "reference_random_split_f1": 0.792,  # produção pós-fix P7 (README.md/paper.tex);
                                                  # 0.997 era o número pré-fix, com lat_norm
                                                  # como atalho de lookup (não generalizava OOD)
            "folds": resultados,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResultados salvos em: {out_path}")


if __name__ == "__main__":
    main()
