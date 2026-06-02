"""
P6 — Gera relatório de interpretabilidade: GradCAM + atribuição física + calibração.

Uso:
    python -m model.run_interpret
    DATA_MODE=mock python -m model.run_interpret

Saída em model/interpretability/
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path

import torch
from torch.utils.data import DataLoader, random_split

from model.interpret import calibration_curve, gradcam_coordinate, physics_attribution, shap_attribution

OUTPUT_DIR = Path("model/interpretability")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# PSRs confirmados + negativos — benchmark 14/14
LOCATIONS = [
    # Positivos
    {"name": "Cabeus",     "lat": -85.5, "lon": -44.6, "expected": 1},
    {"name": "Shackleton", "lat": -89.9, "lon":   0.0, "expected": 1},
    {"name": "Haworth",    "lat": -87.5, "lon":  -5.0, "expected": 1},
    {"name": "Nobile",     "lat": -85.2, "lon":  53.5, "expected": 1},
    {"name": "Sylvester",  "lat": -79.4, "lon": -79.6, "expected": 1},
    {"name": "Hermite",    "lat":  86.0, "lon": -90.0, "expected": 1},
    {"name": "Peary",      "lat":  88.6, "lon":  33.0, "expected": 1},
    {"name": "Whipple",    "lat":  89.0, "lon": -90.0, "expected": 1},
    # Negativos
    {"name": "Equador",    "lat":   0.0, "lon":   0.0, "expected": 0},
    {"name": "MareTranq",  "lat":   0.7, "lon":  23.5, "expected": 0},
    {"name": "Tycho",      "lat": -43.3, "lon": -11.2, "expected": 0},
    {"name": "Copernicus", "lat":   9.6, "lon": -20.1, "expected": 0},
]


def main() -> None:
    print("=== P6 — Interpretabilidade Científica ===\n")
    report: list[dict] = []

    # ── 1. GradCAM + atribuição física por coordenada ─────────────────────────
    print("1. GradCAM + atribuição física por coordenada:")
    print(f"   {'Local':15s}  {'P(gelo)':>7}  {'OK':>3}  Feature dominante")
    print("   " + "-" * 55)

    for loc in LOCATIONS:
        name = loc["name"]
        lat, lon = loc["lat"], loc["lon"]

        cam_result = gradcam_coordinate(
            lat=lat,
            lon=lon,
            save_path=str(OUTPUT_DIR / f"gradcam_{name.lower()}.png"),
        )

        # SHAP com fallback para gradient attribution se shap não instalado
        try:
            attr = shap_attribution(lat=lat)
            attr_method = "shap"
        except ImportError:
            attr = physics_attribution(lat=lat)
            attr_method = "gradient"

        correct = (cam_result["prob"] >= 0.5) == bool(loc["expected"])
        top_feat = max(attr, key=attr.get)

        entry = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "expected": loc["expected"],
            "prob": cam_result["prob"],
            "correct": correct,
            "attribution_method": attr_method,
            "physics_attribution": attr,
        }
        report.append(entry)

        print(
            f"   {name:15s}  {cam_result['prob']:>7.3f}  "
            f"{'✓' if correct else '✗':>3}  "
            f"{top_feat} ({attr[top_feat]:.1%})  [{attr_method}]"
        )

    n_correct = sum(e["correct"] for e in report)
    print(f"\n   {n_correct}/{len(report)} locais preditos corretamente")

    # ── 2. Atribuição média por feature ───────────────────────────────────────
    print("\n2. Atribuição média por feature física (positivos vs negativos):")
    from model.interpret import FEATURE_NAMES

    for label_val, label_name in [(1, "PSRs positivos"), (0, "negativos")]:
        group = [e for e in report if e["expected"] == label_val]
        if not group:
            continue
        avg = {
            f: round(sum(e["physics_attribution"][f] for e in group) / len(group), 4)
            for f in FEATURE_NAMES
        }
        ranked = sorted(avg.items(), key=lambda x: x[1], reverse=True)
        print(f"   {label_name}:")
        for feat, val in ranked:
            bar = "█" * int(val * 30)
            print(f"     {feat:12s}  {val:.1%}  {bar}")

    # ── 3. Calibração MC Dropout ───────────────────────────────────────────────
    print("\n3. Curva de calibração MC Dropout:")
    cal_summary: dict = {}
    try:
        from data.data_pipeline.dataset import LunarDataset

        mode = os.getenv("DATA_MODE", "real")
        dataset = LunarDataset(mode=mode, augment=False)
        n = len(dataset)
        n_val = max(32, int(0.2 * n))
        _, val_ds = random_split(dataset, [n - n_val, n_val])
        val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

        cal = calibration_curve(
            val_loader,
            n_bins=10,
            n_passes=30,
            save_path=str(OUTPUT_DIR / "calibration_curve.png"),
        )
        cal_summary = {"ece": cal["ece"], "n_samples": sum(cal["counts"])}
        print(f"   ECE = {cal['ece']:.4f}  ({sum(cal['counts'])} amostras, {len(cal['bin_centers'])} bins)")
        print("   (ECE < 0.05 é bem calibrado; > 0.1 indica subestimação ou superestimação sistemática)")
    except Exception as exc:
        cal_summary = {"ece": None, "error": str(exc)}
        print(f"   Calibração ignorada: {exc}")

    # ── 4. Salva relatório JSON ────────────────────────────────────────────────
    full_report = {"locations": report, "calibration": cal_summary}
    report_path = OUTPUT_DIR / "interpretability_report.json"
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False))

    print(f"\nFiguras e relatório JSON em: {OUTPUT_DIR}/")
    print("  gradcam_<local>.png  — mapa de ativação por coordenada")
    print("  calibration_curve.png — reliability diagram + distribuição por bin")
    print("  interpretability_report.json — atribuições + ECE completo")


if __name__ == "__main__":
    main()
