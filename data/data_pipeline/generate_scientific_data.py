"""
Gerador de dados científicos para o Lunar Ice Intelligence.

Baseado em publicações reais do LRO (Lunar Reconnaissance Orbiter):
- Paige et al. (2010) Science 330, 479 — Diviner temperatures, PSR measurements
- Mazarico et al. (2011) Icarus 211, 1066 — LOLA illumination conditions
- Hayne et al. (2015) JGR Planets — Regolith thermophysical properties
- Vasavada et al. (2012) JGR Planets — Regolith thermal properties subsurface
- Speyerer & Robinson (2013) Icarus 222, 122 — LROC WAC illumination mapping

Grade: 180 × 360 (1 grau por pixel)
  - Linha i → latitude: -90° + i°  (i = 0..179)
  - Coluna j → longitude: -180° + j°  (j = 0..359)

PSRs conhecidos usados como referência:
  - South: Shackleton (89.9°S), Haworth (87.4°S), Nobile (85.2°S, 53.5°E),
           Cabeus (85.3°S, 35.5°W), Amundsen (84.5°S, 84.7°E)
  - North: Peary (88.6°N, 33°E), Hermite (86.1°N, 89.9°W),
           Whipple (89.0°N, 119.9°E), Byrd (85.0°N, 9.7°E)
"""

import os
import sys
import numpy as np
from model.physics import Z_SKIN, TEMP_ESPACO

# ─── Constantes físicas baseadas em publicações ───────────────────────────────
SOLAR_CONSTANT = 1361.0      # W/m² — medido por TIM/SORCE
TEMP_ICE_STABLE = 110.0      # K — sublimação de H2O (Zhang & Paige 2009)
TEMP_PSR_MIN    = 26.0       # K — mínimo medido (Hermite crater, Paige 2010)
TEMP_EQUATORIAL = 250.0      # K — média anual equatorial (Diviner global map)
STEFAN_BOLTZMANN = 5.670374419e-8

# PSRs confirmados pelo LRO — (lat_deg, lon_deg, raio_graus, T_media_K)
# Valores de temperatura de Paige et al. (2010) Table 1 e Supplementary
PSRS_CONHECIDOS = [
    # Polo Sul
    (-89.9,   0.0,  0.8,  33.0),   # Shackleton
    (-87.4,  -4.7,  1.2,  52.0),   # Haworth
    (-85.2,  53.5,  1.5,  61.0),   # Nobile
    (-85.3, -35.5,  1.2,  57.0),   # Cabeus (onde LCROSS confirmou gelo em 2009)
    (-84.5,  84.7,  1.8,  70.0),   # Amundsen
    (-83.0, -90.0,  1.0,  75.0),   # Unnamed South PSR
    # Polo Norte
    ( 88.6,  33.0,  0.9,  52.0),   # Peary
    ( 86.1, -89.9,  1.1,  26.0),   # Hermite (mais frio do sistema solar medido)
    ( 89.0, 119.9,  0.7,  40.0),   # Whipple
    ( 85.0,   9.7,  1.3,  65.0),   # Byrd
    ( 84.0, -52.0,  1.0,  70.0),   # Unnamed North PSR
]


# ─── Modelo de temperatura (Diviner) ─────────────────────────────────────────

def temperatura_diviner(lat_grid, lon_grid):
    """
    Temperatura anual média baseada no instrumento Diviner (Paige et al. 2010).
    Retorna array (180, 360) em Kelvin.
    """
    rng = np.random.default_rng(42)
    H, W = lat_grid.shape
    temp = np.zeros((H, W), dtype=np.float32)

    abs_lat = np.abs(lat_grid)

    # ── Modelo base por faixa de latitude ────────────────────────────────────
    # Equatorial-tropical (0–60°): média anual Diviner ~250K
    mask_eq = abs_lat <= 60
    temp[mask_eq] = (
        TEMP_EQUATORIAL * (0.7 + 0.3 * np.cos(np.radians(abs_lat[mask_eq])))
        + rng.normal(0, 15, mask_eq.sum())
    )
    temp[mask_eq] = np.clip(temp[mask_eq], 150, 400)

    # Média latitude alta (60–75°): transição para polar
    mask_hi = (abs_lat > 60) & (abs_lat <= 75)
    frac = (abs_lat[mask_hi] - 60) / 15
    temp[mask_hi] = (
        TEMP_EQUATORIAL * (1 - frac) + 130 * frac
        + rng.normal(0, 20, mask_hi.sum())
    )
    temp[mask_hi] = np.clip(temp[mask_hi], 80, 280)

    # Polar (75–82°): influência de PSRs
    mask_p = (abs_lat > 75) & (abs_lat <= 82)
    frac = (abs_lat[mask_p] - 75) / 7
    temp[mask_p] = (
        130 * (1 - frac) + 95 * frac
        + rng.normal(0, 15, mask_p.sum())
    )
    temp[mask_p] = np.clip(temp[mask_p], 55, 180)

    # Alta polar (82–87°): PSRs frequentes
    mask_dp = (abs_lat > 82) & (abs_lat <= 87)
    frac = (abs_lat[mask_dp] - 82) / 5
    temp[mask_dp] = (
        95 * (1 - frac) + 65 * frac
        + rng.normal(0, 10, mask_dp.sum())
    )
    temp[mask_dp] = np.clip(temp[mask_dp], 40, 130)

    # Extremo polar (>87°): PSRs dominantes
    mask_xp = abs_lat > 87
    temp[mask_xp] = (
        55 + rng.normal(0, 12, mask_xp.sum())
    )
    temp[mask_xp] = np.clip(temp[mask_xp], TEMP_PSR_MIN, 100)

    # ── PSRs conhecidos: cold spots gaussianos ────────────────────────────────
    for (lat_c, lon_c, raio, T_psr) in PSRS_CONHECIDOS:
        # Converter para índices de grade — clip para manter dentro dos bounds (H=180, W=360)
        i_c = int(np.clip(round(lat_c + 90), 0, H - 1))
        j_c = int(np.clip(round(lon_c + 180), 0, W - 1))

        raio_px = int(raio * 1.5) + 2
        i_min = max(0, i_c - raio_px)
        i_max = min(H, i_c + raio_px + 1)
        j_min = max(0, j_c - raio_px)
        j_max = min(W, j_c + raio_px + 1)

        for ii in range(i_min, i_max):
            for jj in range(j_min, j_max):
                dlat = lat_grid[ii, jj] - lat_c
                dlon = lon_grid[ii, jj] - lon_c
                dist = np.sqrt(dlat**2 + dlon**2)
                if dist < raio:
                    # Perfil gaussiano dentro do PSR
                    weight = np.exp(-(dist / (raio * 0.5))**2)
                    temp[ii, jj] = T_psr * weight + temp[ii, jj] * (1 - weight)

    return temp.clip(TEMP_PSR_MIN, 420)


# ─── Modelo de insolação (LOLA, Mazarico 2011) ───────────────────────────────

def insolacao_lola(lat_grid, lon_grid):
    """
    Fração de iluminação anual média baseada em LOLA (Mazarico et al. 2011).
    Retorna array (180, 360) em W/m².
    """
    rng = np.random.default_rng(123)
    H, W = lat_grid.shape
    insol = np.zeros((H, W), dtype=np.float32)

    abs_lat = np.abs(lat_grid)

    # Modelo de fração de iluminação anual por latitude
    # Fonte: Mazarico et al. (2011) Figure 3
    frac = np.zeros((H, W), dtype=np.float32)

    mask_eq = abs_lat <= 60
    frac[mask_eq] = np.cos(np.radians(abs_lat[mask_eq])) * 0.55 + 0.1

    mask_hi = (abs_lat > 60) & (abs_lat <= 75)
    frac[mask_hi] = 0.35 - (abs_lat[mask_hi] - 60) / 15 * 0.15

    mask_p = (abs_lat > 75) & (abs_lat <= 82)
    frac[mask_p] = 0.20 - (abs_lat[mask_p] - 75) / 7 * 0.10

    mask_dp = (abs_lat > 82) & (abs_lat <= 87)
    frac[mask_dp] = 0.10 - (abs_lat[mask_dp] - 82) / 5 * 0.08

    mask_xp = abs_lat > 87
    frac[mask_xp] = 0.02

    # Ruído realista
    frac += rng.normal(0, 0.02, (H, W))
    frac = np.clip(frac, 0.0, 1.0)

    # PSRs — iluminação próxima de zero
    for (lat_c, lon_c, raio, _) in PSRS_CONHECIDOS:
        i_c = int(np.clip(round(lat_c + 90), 0, H - 1))
        j_c = int(np.clip(round(lon_c + 180), 0, W - 1))
        raio_px = int(raio * 1.5) + 2
        i_min = max(0, i_c - raio_px)
        i_max = min(H, i_c + raio_px + 1)
        j_min = max(0, j_c - raio_px)
        j_max = min(W, j_c + raio_px + 1)

        for ii in range(i_min, i_max):
            for jj in range(j_min, j_max):
                dlat = lat_grid[ii, jj] - lat_c
                dlon = lon_grid[ii, jj] - lon_c
                dist = np.sqrt(dlat**2 + dlon**2)
                if dist < raio:
                    weight = np.exp(-(dist / (raio * 0.5))**2)
                    frac[ii, jj] *= (1 - weight * 0.98)

    insol = frac * SOLAR_CONSTANT
    return insol.astype(np.float32)


# ─── Modelo subsuperficial (Vasavada 2012) ───────────────────────────────────

def temperatura_subsolo_grid(temp_superficie, profundidade=2.0, camadas=20):
    """
    Solução analítica da equação de difusão térmica para toda a grade (vetorizada).

    T(z) = T_mean + (T_sup - T_mean) * exp(-z / z_skin)
    Ref: Vasavada et al. 2012, JGR Planets.

    Args:
        temp_superficie: array (H, W) — temperatura média anual superficial (K)
        profundidade: profundidade máxima em metros
        camadas: número de camadas discretas

    Returns:
        np.ndarray shape (H, W, camadas) — temperatura por profundidade (K)
    """
    # Temperatura de equilíbrio profundo: 80% da superfície, mínimo 3K
    T_mean = np.maximum(temp_superficie * 0.8, TEMP_ESPACO)   # (H, W)

    profundidades = np.linspace(0.0, profundidade, camadas)    # (camadas,)

    # Broadcasting: (H, W, 1) op (1, 1, camadas) → (H, W, camadas)
    delta = (temp_superficie - T_mean)[:, :, None]             # (H, W, 1)
    decay = np.exp(-profundidades[None, None, :] / Z_SKIN)     # (1, 1, camadas)

    subsolo = T_mean[:, :, None] + delta * decay               # (H, W, camadas)
    return subsolo.astype(np.float32)


# ─── Patches LROC-like ────────────────────────────────────────────────────────

def gerar_patches_lroc(n=50, size=64):
    """
    Gera n patches de imagem simulando textura LROC WAC.

    Tipos baseados em características reais do terreno lunar:
    - Tipo PSR (i < 15): crater escuro com anel brilhante (PSR)
    - Tipo polar (15 <= i < 30): terreno polar com crateras
    - Tipo equatorial (30 <= i): terreno equatorial claro
    """
    rng = np.random.default_rng(7)
    patches = []

    for i in range(n):
        patch = np.zeros((size, size), dtype=np.float32)
        y, x = np.mgrid[0:size, 0:size]

        if i < 15:
            # PSR: fundo escuro (albedo ~0.05-0.10), anel brilhante
            patch[:] = rng.uniform(0.04, 0.12)  # albedo lunar típico PSR
            cx, cy = size // 2, size // 2
            r_inner = size * rng.uniform(0.25, 0.35)
            r_outer = r_inner * rng.uniform(1.3, 1.6)
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            # Interior PSR (mais escuro)
            patch[dist < r_inner] = rng.uniform(0.02, 0.06)
            # Anel brilhante (rim iluminado)
            rim = (dist >= r_inner) & (dist < r_outer)
            patch[rim] = rng.uniform(0.15, 0.30)
            # Textura de superfície
            noise = rng.normal(0, 0.01, (size, size))
            patch += noise
        elif i < 30:
            # Terreno polar: albedo médio, múltiplas crateras pequenas
            patch[:] = rng.uniform(0.10, 0.18)
            n_craters = rng.integers(3, 8)
            for _ in range(n_craters):
                cx = rng.integers(5, size - 5)
                cy = rng.integers(5, size - 5)
                r = rng.uniform(2, 8)
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                patch[dist < r * 0.7] = rng.uniform(0.06, 0.12)
                rim = (dist >= r * 0.7) & (dist < r)
                patch[rim] = rng.uniform(0.20, 0.35)
            noise = rng.normal(0, 0.015, (size, size))
            patch += noise
        else:
            # Equatorial: albedo alto, textura variada
            patch[:] = rng.uniform(0.15, 0.25)
            # Albedo variações por regolito
            for _ in range(rng.integers(1, 4)):
                cx = rng.integers(0, size)
                cy = rng.integers(0, size)
                sigma = rng.uniform(8, 25)
                strength = rng.uniform(-0.05, 0.08)
                blob = np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))
                patch += strength * blob
            noise = rng.normal(0, 0.02, (size, size))
            patch += noise

        patch = np.clip(patch, 0.0, 1.0).astype(np.float32)
        patches.append(patch)

    return patches


# ─── Pipeline principal ───────────────────────────────────────────────────────

def gerar_dados(out_dir, modo="real", verbose=True):
    """
    Gera dados científicos e salva no diretório indicado.

    modo="real" → dados baseados em publicações (180×360)
    modo="mock" → dados simplificados e rápidos (64×64)
    """
    os.makedirs(out_dir, exist_ok=True)
    img_dir = os.path.join(out_dir, "imagens")
    os.makedirs(img_dir, exist_ok=True)

    if modo == "real":
        H, W = 180, 360
    else:
        H, W = 64, 64

    if verbose:
        print(f"[{modo.upper()}] Grade {H}x{W} -> {out_dir}")

    # Grades de latitude e longitude
    lat_vals = np.linspace(-89.5, 89.5, H)
    lon_vals = np.linspace(-179.5, 179.5, W)
    lon_grid, lat_grid = np.meshgrid(lon_vals, lat_vals)

    # ── Temperatura ───────────────────────────────────────────────────────────
    if verbose:
        print("  Gerando temperatura (modelo Diviner / Paige 2010)...")

    if modo == "real":
        temp = temperatura_diviner(lat_grid, lon_grid)
    else:
        # Mock: cálculo rápido baseado apenas na latitude
        rng = np.random.default_rng(99)
        abs_lat = np.abs(lat_grid)
        temp = np.where(
            abs_lat > 80,
            rng.uniform(30, 110, (H, W)),
            TEMP_EQUATORIAL - abs_lat * 1.8 + rng.normal(0, 20, (H, W))
        ).astype(np.float32)
        temp = np.clip(temp, TEMP_PSR_MIN, 420)

    np.save(os.path.join(out_dir, "temperatura.npy"), temp)
    if verbose:
        print(f"    min={temp.min():.1f}K  max={temp.max():.1f}K  media={temp.mean():.1f}K")

    # ── Temperatura subsuperficial (difusão térmica, Vasavada 2012) ───────────
    if verbose:
        print("  Gerando temperatura subsuperficial (20 camadas, 0-2m)...")

    subsolo = temperatura_subsolo_grid(temp, profundidade=2.0, camadas=20)
    np.save(os.path.join(out_dir, "temperatura_subsolo.npy"), subsolo)
    if verbose:
        camada_1m = subsolo[:, :, 9]   # índice ~1m de profundidade
        n_estavel = int(np.sum(subsolo.min(axis=2) < 110.0))
        print(f"    shape={subsolo.shape}  T@1m: {camada_1m.min():.1f}K-{camada_1m.max():.1f}K")
        print(f"    pixels com gelo estavel em subsolo: {n_estavel} ({n_estavel/subsolo.shape[0]/subsolo.shape[1]*100:.1f}%)")

    # ── Insolação ─────────────────────────────────────────────────────────────
    if verbose:
        print("  Gerando insolação (modelo LOLA / Mazarico 2011)...")

    if modo == "real":
        insol = insolacao_lola(lat_grid, lon_grid)
    else:
        rng = np.random.default_rng(88)
        abs_lat = np.abs(lat_grid)
        frac = np.where(
            abs_lat > 85,
            rng.uniform(0, 0.05, (H, W)),
            np.cos(np.radians(abs_lat)) * 0.5 + rng.normal(0, 0.05, (H, W))
        )
        insol = (np.clip(frac, 0, 1) * SOLAR_CONSTANT).astype(np.float32)

    np.save(os.path.join(out_dir, "insolacao.npy"), insol)
    if verbose:
        print(f"    min={insol.min():.1f}  max={insol.max():.1f}  media={insol.mean():.1f} W/m²")

    # ── Labels de gelo ────────────────────────────────────────────────────────
    # Labels sao gerados por generate_labels.py (PSRs confirmados por instrumentos
    # independentes). Gerar labels aqui por threshold(temp, insol) introduziria
    # circularidade: o modelo aprenderia o threshold em vez de detectar gelo real.
    # Chama salvar_labels() apenas se o arquivo ainda nao existir (setup inicial).
    labels_path = os.path.join(out_dir, "labels_gelo.npy")
    if not os.path.exists(labels_path):
        from data.data_pipeline.generate_labels import salvar_labels
        salvar_labels(out_dir=out_dir, verbose=verbose)
    elif verbose:
        existing = np.load(labels_path)
        print(f"  Labels existentes: {int(existing.sum())} positivos (PSR-based, mantidos)")

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = np.array([{
        "source": "LRO Diviner + LOLA (modeled)",
        "reference_temperature": "Paige et al. (2010) Science 330, 479",
        "reference_illumination": "Mazarico et al. (2011) Icarus 211, 1066",
        "grid_shape": [H, W],
        "lat_range": [-89.5, 89.5],
        "lon_range": [-179.5, 179.5],
        "resolution_deg": 180 / H,
        "temperature_unit": "Kelvin",
        "insolation_unit": "W/m2",
        "ice_stable_threshold_K": TEMP_ICE_STABLE,
        "psrs_modeled": [p[:2] for p in PSRS_CONHECIDOS],
    }], dtype=object)
    np.save(os.path.join(out_dir, "metadata.npy"), metadata)

    # ── Imagens LROC-like ─────────────────────────────────────────────────────
    if verbose:
        print("  Gerando 50 patches LROC-like (64×64)...")

    patches = gerar_patches_lroc(n=50, size=64)
    for idx, patch in enumerate(patches):
        np.save(os.path.join(img_dir, f"img_{idx:03d}.npy"), patch)

    if verbose:
        print(f"  Dados salvos em: {out_dir}")
        print("  Concluído.")


# ─── Verificação dos dados ────────────────────────────────────────────────────

def verificar_dados(out_dir):
    """Valida integridade dos arquivos gerados."""
    erros = []

    for nome in ["temperatura.npy", "temperatura_subsolo.npy", "insolacao.npy", "metadata.npy"]:
        path = os.path.join(out_dir, nome)
        if not os.path.exists(path):
            erros.append(f"Faltando: {nome}")
            continue
        arr = np.load(path, allow_pickle=True)
        if hasattr(arr, "size") and arr.size == 0:
            erros.append(f"Vazio: {nome}")

    img_dir = os.path.join(out_dir, "imagens")
    imgs = [f for f in os.listdir(img_dir) if f.endswith(".npy")] if os.path.isdir(img_dir) else []
    if len(imgs) < 50:
        erros.append(f"Imagens: {len(imgs)}/50 encontradas")

    if erros:
        for e in erros:
            print(f"  [ERRO] {e}")
        return False

    temp   = np.load(os.path.join(out_dir, "temperatura.npy"))
    subsol = np.load(os.path.join(out_dir, "temperatura_subsolo.npy"))
    insol  = np.load(os.path.join(out_dir, "insolacao.npy"))
    print(f"  [OK] temperatura:         {temp.shape} — {temp.min():.1f}K a {temp.max():.1f}K")
    print(f"  [OK] temperatura_subsolo: {subsol.shape} — {subsol.min():.1f}K a {subsol.max():.1f}K")
    print(f"  [OK] insolacao:           {insol.shape} — {insol.min():.1f} a {insol.max():.1f} W/m²")
    print(f"  [OK] imagens:             {len(imgs)} patches")
    return True


# ─── Execução direta ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gera dados científicos LRO")
    parser.add_argument("--modo", choices=["real", "mock", "ambos"], default="ambos")
    parser.add_argument("--base", default="data/processed/lro")
    args = parser.parse_args()

    if args.modo in ("real", "ambos"):
        print("\n=== DADOS REAIS (Diviner + LOLA model) ===")
        gerar_dados(args.base, modo="real")
        print("\nVerificação:")
        verificar_dados(args.base)

    if args.modo in ("mock", "ambos"):
        print("\n=== DADOS MOCK (simplificados) ===")
        mock_dir = os.path.join(args.base, "mock")
        gerar_dados(mock_dir, modo="mock")
        print("\nVerificação:")
        verificar_dados(mock_dir)
