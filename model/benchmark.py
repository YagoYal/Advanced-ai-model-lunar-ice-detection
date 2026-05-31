"""
Benchmark do modelo contra catálogos PSR publicados.

Fontes:
  Mazarico et al. (2011) Icarus 211 — LOLA illumination, PSR catalog
  Hayne et al. (2015) JGR — Diviner temperatura mínima anual
  Spudis et al. (2010) GRL — Mini-RF CPR detecção de gelo norte
  Colaprete et al. (2010) Science — LCROSS Cabeus confirmação direta

Execução:
  python -m model.benchmark
"""

import os, sys
import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model.cnn import LunarCNN
from model.physics import temperatura_superficie, features_subsolo
from data.data_pipeline.coords import graus_para_grid

WEIGHTS = "model/pesos.pth"
DEVICE  = torch.device("cpu")

# ─── Catálogo PSR com base em publicações ─────────────────────────────────────
# (nome, lat, lon, gelo_esperado, conf, referencia)
CATALOGO = [
    # Polo Sul — gelo confirmado
    ("Cabeus",         -85.32, -35.50, True,  1.00, "Colaprete 2010 Science — LCROSS impacto"),
    ("Shackleton",     -89.90,   0.00, True,  0.90, "Gladstone 2010 Science — LAMP UV"),
    ("Haworth",        -87.40,  -4.70, True,  0.80, "Spudis 2010 GRL — Mini-RF CPR>1.0"),
    ("Nobile",         -85.20,  53.50, True,  0.75, "Hayne 2015 JGR — cold trap Diviner"),
    ("Amundsen",       -84.50,  84.70, True,  0.70, "Mazarico 2011 Icarus — PSR catalog"),
    # Polo Norte — gelo confirmado
    ("Hermite",         86.10, -89.90, True,  0.90, "Paige 2010 Science — 26K mais frio medido"),
    ("Peary",           88.60,  33.00, True,  0.85, "Spudis 2013 JGR — CPR norte"),
    ("Whipple",         89.00, 119.90, True,  0.80, "Mazarico 2011 — PSR norte"),
    # Negativos confirmados — sem gelo
    ("Equador_0N",       0.00,   0.00, False, 1.00, "Nenhum instrumento detectou gelo"),
    ("Mare_Tranq",       0.67,  23.47, False, 1.00, "Apollo 11 — solo basaltico, sem gelo"),
    ("Copernicus",      -9.70, -20.00, False, 0.95, "Crater jovem, sem PSR"),
    ("Tycho",          -43.30, -11.20, False, 0.95, "Mid-lat, temperatura alta"),
    ("Mid_lat_40N",     40.00,  60.00, False, 0.90, "Terreno iluminado, sem PSR"),
    ("Mid_lat_40S",    -40.00, -60.00, False, 0.90, "Terreno iluminado, sem PSR"),
]


def rodar_benchmark() -> dict:
    if not os.path.exists(WEIGHTS):
        print(f"Modelo nao encontrado: {WEIGHTS}")
        print("Rode: python -m model.train")
        return {}

    model = LunarCNN().to(DEVICE)
    model.load_state_dict(torch.load(WEIGHTS, map_location=DEVICE, weights_only=True))
    model.eval()

    insol_map = None
    insol_path = "data/processed/lro/insolacao.npy"
    if os.path.exists(insol_path):
        insol_map = np.load(insol_path)

    print(f"Benchmark — {len(CATALOGO)} locais catalogados\n")
    print(f"{'Local':<16} {'Lat':>7} {'Lon':>7} {'Prob':>6}  {'Esperado':>8}  {'OK':>3}  Referencia")
    print("-" * 90)

    resultados = []
    for nome, lat, lon, ice_esperado, conf, ref in CATALOGO:
        i, j = graus_para_grid(lat, lon)

        insol = float(insol_map[i, j]) if insol_map is not None else 500.0
        insol_n = insol / 1361.0
        lat_n   = lat   / 90.0

        temp_sup  = temperatura_superficie(insol)
        sub_feats = features_subsolo(temp_sup, insolacao=insol)

        img    = np.zeros((64, 64), dtype=np.float32)
        img_t  = torch.tensor(img).unsqueeze(0).unsqueeze(0).to(DEVICE)
        feat_t = torch.tensor([[insol_n, lat_n,
                                float(sub_feats[0]),
                                float(sub_feats[1]),
                                float(sub_feats[2])]]).to(DEVICE)

        with torch.no_grad():
            prob = model(img_t, feat_t).item()

        pred_ice  = prob > 0.5
        correto   = pred_ice == ice_esperado
        simbolo   = "OK" if correto else "!!"
        esperado_str = "GELO" if ice_esperado else "SEM"
        pred_str     = "GELO" if pred_ice   else "SEM"

        print(f"{nome:<16} {lat:>+7.1f} {lon:>+7.1f} {prob:>6.3f}  {esperado_str:>8}  {simbolo:>3}  {ref[:45]}")

        resultados.append({
            "nome": nome, "lat": lat, "lon": lon,
            "prob": prob, "ice_esperado": ice_esperado,
            "correto": correto, "conf": conf,
        })

    n_ok   = sum(r["correto"] for r in resultados)
    n_tot  = len(resultados)
    n_pos  = sum(r["ice_esperado"] for r in resultados)
    n_neg  = n_tot - n_pos

    # Precisao separada por categoria
    ok_pos = sum(r["correto"] for r in resultados if r["ice_esperado"])
    ok_neg = sum(r["correto"] for r in resultados if not r["ice_esperado"])

    print(f"\n{'='*90}")
    print(f"Total: {n_ok}/{n_tot} corretos ({100*n_ok/n_tot:.0f}%)")
    print(f"  PSRs (gelo)    : {ok_pos}/{n_pos} corretos")
    print(f"  Negativos      : {ok_neg}/{n_neg} corretos")

    if n_ok == n_tot:
        print("Modelo passou em todos os locais catalogados.")
    elif n_ok >= n_tot * 0.8:
        print("Modelo bom — acima de 80% de acerto.")
    else:
        print("Modelo precisa de mais treino ou dados.")

    np.save("model/benchmark_resultados.npy", np.array(resultados, dtype=object))
    return {"total": n_tot, "corretos": n_ok, "psr_ok": ok_pos, "neg_ok": ok_neg}


if __name__ == "__main__":
    rodar_benchmark()
