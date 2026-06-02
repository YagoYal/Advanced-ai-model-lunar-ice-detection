"""
P6 — Interpretabilidade científica.

GradCAM (CNNEncoder conv[10] — última ReLU 16×16×64)
+ atribuição por gradiente×entrada (PhysicsEncoder)
+ curva de calibração MC Dropout (reliability diagram + ECE).
"""
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path

from model.hybrid_model import modelo, DEVICE, preprocessar_imagem, features_fisicas


FEATURE_NAMES = ["insolacao", "lat", "sub_0.1m", "sub_0.5m", "sub_1.0m"]


# ─── GradCAM ──────────────────────────────────────────────────────────────────

class GradCAM:
    """
    GradCAM no último bloco conv do CNNEncoder.

    conv[10] = último ReLU antes do MaxPool final → activations 16×16×64.
    Ref: Selvaraju et al. 2017, Grad-CAM: Visual Explanations from Deep Networks.
    """

    def __init__(self, model=None):
        self._model = model or modelo
        self._act: torch.Tensor | None = None
        self._grad: torch.Tensor | None = None
        target = self._model.cnn.conv[10]
        target.register_forward_hook(self._fwd_hook)
        target.register_full_backward_hook(self._bwd_hook)

    def _fwd_hook(self, module, inp, out):
        self._act = out.detach()

    def _bwd_hook(self, module, grad_inp, grad_out):
        self._grad = grad_out[0].detach()

    def compute(self, img_t: torch.Tensor, env_t: torch.Tensor) -> tuple[np.ndarray, float]:
        """
        Retorna (cam 64×64 normalizado [0,1], probabilidade de gelo).
        img_t: [1,1,64,64]  env_t: [1,5]
        """
        self._model.train()
        for m in self._model.modules():
            if isinstance(m, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d)):
                m.eval()

        self._model.zero_grad()
        prob = self._model(img_t, env_t)
        prob.backward()
        self._model.eval()

        # global-average-pool dos gradientes → pesos por canal
        weights = self._grad.mean(dim=(2, 3), keepdim=True)   # [1, 64, 1, 1]
        cam = (weights * self._act).sum(dim=1, keepdim=True)  # [1, 1, 16, 16]
        cam = F.relu(cam)

        cam_up = F.interpolate(cam, size=(64, 64), mode="bilinear", align_corners=False)
        cam_np = cam_up.squeeze().cpu().numpy()

        if cam_np.max() > cam_np.min():
            cam_np = (cam_np - cam_np.min()) / (cam_np.max() - cam_np.min())

        return cam_np, float(prob.item())


def gradcam_coordinate(lat: float, lon: float = 0.0, insolacao: float = 0.0,
                        temperatura: float = None, save_path: str = None) -> dict:
    """
    Roda GradCAM para uma coordenada lunar.
    Salva figura PNG se save_path fornecido.
    """
    img_t = preprocessar_imagem(None)
    env_t = features_fisicas(insolacao, lat, temp_superficie=temperatura)

    gcam = GradCAM()
    cam, prob = gcam.compute(img_t, env_t)

    result = {"cam": cam, "prob": round(prob, 4), "lat": lat, "lon": lon}

    if save_path:
        _plot_gradcam(img_t.squeeze().cpu().numpy(), cam, prob, lat, lon, save_path)

    return result


def _plot_gradcam(img: np.ndarray, cam: np.ndarray, prob: float,
                   lat: float, lon: float, path: str) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle(
        f"GradCAM — lat={lat:.1f}°  lon={lon:.1f}°  P(gelo)={prob:.3f}",
        fontsize=12,
    )

    axes[0].imshow(img, cmap="gray", vmin=0, vmax=1)
    axes[0].set_title("Patch de entrada")
    axes[0].axis("off")

    axes[1].imshow(img, cmap="gray", vmin=0, vmax=1)
    axes[1].imshow(cam, cmap="jet", alpha=0.55, vmin=0, vmax=1)
    axes[1].set_title("GradCAM (vermelho = alta ativação)")
    axes[1].axis("off")

    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    sm = plt.cm.ScalarMappable(cmap="jet", norm=plt.Normalize(0, 1))
    fig.colorbar(sm, cax=cbar_ax, label="Ativação normalizada")

    plt.tight_layout(rect=[0, 0, 0.91, 1])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


# ─── Atribuição de features físicas ──────────────────────────────────────────

def physics_attribution(lat: float, insolacao: float = 0.0,
                         temperatura: float = None) -> dict[str, float]:
    """
    Atribuição por gradiente × entrada (Saliency × Input) para o PhysicsEncoder.
    Retorna contribuição relativa de cada feature (soma = 1.0).
    """
    env_t = features_fisicas(insolacao, lat, temp_superficie=temperatura)
    env_t.requires_grad_(True)
    img_t = preprocessar_imagem(None)

    modelo.train()
    for m in modelo.modules():
        if isinstance(m, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d)):
            m.eval()

    prob = modelo(img_t, env_t)
    prob.backward()
    modelo.eval()

    grads = env_t.grad.squeeze().cpu().detach().numpy()
    vals  = env_t.detach().squeeze().cpu().numpy()
    attr  = np.abs(grads * vals)
    total = attr.sum() or 1.0

    return {name: round(float(attr[i] / total), 4) for i, name in enumerate(FEATURE_NAMES)}


# ─── SHAP attribution (GradientExplainer) ────────────────────────────────────

def shap_attribution(lat: float, insolacao: float = 0.0, temperatura: float = None,
                      n_background: int = 50) -> dict[str, float]:
    """
    SHAP attribution via GradientExplainer para o PhysicsEncoder.

    A imagem é zerada no wrapper para que toda a variação da saída seja atribuída
    às features físicas — isolando a contribuição do PhysicsEncoder.

    n_background: amostras de background uniformes no espaço normalizado [0, 0.5].
    Ref: Lundberg & Lee 2017, A Unified Approach to Interpreting Model Predictions.
    """
    try:
        import shap
    except ImportError as exc:
        raise ImportError("pip install shap para usar shap_attribution()") from exc

    class _PhysicsWrapper(torch.nn.Module):
        """Expõe apenas as features físicas — imagem fixa em zero."""
        def forward(self, env: torch.Tensor) -> torch.Tensor:
            img = torch.zeros(env.shape[0], 1, 64, 64, device=env.device)
            return modelo(img, env)

    wrapper = _PhysicsWrapper().to(DEVICE)
    wrapper.eval()

    bg = torch.rand(n_background, 5, dtype=torch.float32, device=DEVICE) * 0.5
    explainer = shap.GradientExplainer(wrapper, bg)

    env_t = features_fisicas(insolacao, lat, temp_superficie=temperatura)  # [1, 5]
    raw = explainer.shap_values(env_t)

    # GradientExplainer pode retornar lista (classificação) ou ndarray (regressão)
    vals_np: np.ndarray = np.abs(raw[0] if isinstance(raw, list) else raw).flatten()

    total = vals_np.sum() or 1.0
    return {name: round(float(vals_np[i] / total), 4) for i, name in enumerate(FEATURE_NAMES)}


# ─── Calibration curve (MC Dropout) ──────────────────────────────────────────

def calibration_curve(val_loader, n_bins: int = 10, n_passes: int = 30,
                       save_path: str = None) -> dict:
    """
    Reliability diagram via MC Dropout.

    val_loader deve iterar (img, features, label, *extras).
    Retorna dict com bin_centers, fraction_positive, counts e ECE.
    """
    all_probs: list[float] = []
    all_labels: list[float] = []

    modelo.train()
    for m in modelo.modules():
        if isinstance(m, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d)):
            m.eval()

    with torch.no_grad():
        for img, features, label, *_ in val_loader:
            img      = img.to(DEVICE)
            features = features.to(DEVICE)
            preds    = torch.stack(
                [modelo(img, features).squeeze() for _ in range(n_passes)]
            )  # [n_passes, B]
            means = preds.mean(dim=0).cpu().numpy()
            all_probs.extend(means.tolist())
            all_labels.extend(label.float().numpy().tolist())

    modelo.eval()

    probs  = np.array(all_probs)
    labels = np.array(all_labels)

    edges = np.linspace(0, 1, n_bins + 1)
    centers: list[float] = []
    fracs:   list[float] = []
    counts:  list[int]   = []

    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (probs >= lo) & (probs < hi)
        if not mask.any():
            continue
        centers.append(float((lo + hi) / 2))
        fracs.append(float(labels[mask].mean()))
        counts.append(int(mask.sum()))

    ece = sum(
        counts[i] / len(probs) * abs(fracs[i] - centers[i])
        for i in range(len(centers))
    )

    result = {
        "bin_centers": centers,
        "fraction_positive": fracs,
        "counts": counts,
        "ece": round(float(ece), 4),
    }

    if save_path:
        _plot_calibration(centers, fracs, counts, ece, save_path)

    return result


def _plot_calibration(centers: list, fracs: list, counts: list,
                       ece: float, path: str) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        f"MC Dropout — Curva de Calibração  (ECE = {ece:.4f})",
        fontsize=13,
    )

    width = 0.8 / max(len(centers), 1)

    ax = axes[0]
    ax.plot([0, 1], [0, 1], "k--", lw=1.5, label="Calibração perfeita")
    ax.bar(centers, fracs, width=width, alpha=0.65, color="steelblue", label="Modelo")
    ax.set_xlabel("Probabilidade predita (média MC Dropout)")
    ax.set_ylabel("Fração de positivos reais")
    ax.set_title("Reliability Diagram")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()

    ax2 = axes[1]
    ax2.bar(centers, counts, width=width, alpha=0.7, color="coral")
    ax2.set_xlabel("Bin de probabilidade predita")
    ax2.set_ylabel("Número de amostras")
    ax2.set_title("Distribuição de amostras por bin")

    plt.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
