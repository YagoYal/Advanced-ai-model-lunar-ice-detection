"""
Exporta LunarCNN para ONNX para inferência embarcada ou browser (ONNX Runtime Web).

Uso:
  python -m model.export_onnx                      # salva model/lunar_ice.onnx
  python -m model.export_onnx --output custom.onnx  # caminho customizado

Entradas do modelo ONNX:
  imagem   : float32 [1, 1, 64, 64]
  features : float32 [1, 5]   (insol_norm, lat_norm, sub_0.1m, sub_0.5m, sub_1.0m)

Saída:
  probabilidade : float32 [1, 1]   (probabilidade de gelo ∈ [0,1])
"""

import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model.cnn import LunarCNN

WEIGHTS_PATH = "model/pesos.pth"
DEFAULT_OUT  = "model/lunar_ice.onnx"
OPSET        = 17


def exportar(output_path: str = DEFAULT_OUT) -> None:
    device = torch.device("cpu")

    model = LunarCNN().to(device)

    if not os.path.exists(WEIGHTS_PATH):
        print(f"[WARN] {WEIGHTS_PATH} não encontrado — exportando modelo sem pesos treinados.")
    else:
        model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device, weights_only=True))
        print(f"Pesos carregados de {WEIGHTS_PATH}")

    model.eval()

    dummy_img      = torch.zeros(1, 1, 64, 64, dtype=torch.float32)
    dummy_features = torch.zeros(1, 5,       dtype=torch.float32)

    torch.onnx.export(
        model,
        (dummy_img, dummy_features),
        output_path,
        opset_version=OPSET,
        input_names=["imagem", "features"],
        output_names=["probabilidade"],
        dynamic_axes={
            "imagem":       {0: "batch"},
            "features":     {0: "batch"},
            "probabilidade": {0: "batch"},
        },
    )
    size_mb = os.path.getsize(output_path) / 1e6
    print(f"Exportado: {output_path}  ({size_mb:.2f} MB, opset={OPSET})")

    # Verifica grafo se onnx estiver instalado
    try:
        import onnx
        m = onnx.load(output_path)
        onnx.checker.check_model(m)
        print("onnx.checker: OK")
    except ImportError:
        print("[INFO] onnx não instalado — skip verificação (pip install onnx)")
    except Exception as e:
        print(f"[WARN] onnx.checker falhou: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUT)
    args = parser.parse_args()
    exportar(args.output)
