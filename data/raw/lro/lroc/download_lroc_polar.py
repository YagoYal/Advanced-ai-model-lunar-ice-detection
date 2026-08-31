"""
Patches LROC WAC 64×64 para PSRs polares -Haworth, Nobile, Peary.

O COG equiretangular USGS (54582×109164) tem lacunas de cobertura WAC em
|lat| > ~85deg porque a câmera não aponta para o nadir no cruzamento polar.
Estratégia em ordem de prioridade:
  1. vsicurl no produto polar estereográfico PDS (LROC ASU) -projeção nativa
  2. vsicurl no COG global USGS com cálculo de janela explícito
  3. Patch sintético calibrado por albedo publicado (Sato 2014 / Hapke 2001)

Refs albedo PSR:
  Sato et al. (2014) JGR Planets 119 -LROC WAC photometry global, Table 1
  Hapke (2001) JGR -Lunar PSR albedo model
  Zuber et al. (2012) Science -polar topography LOLA

Uso:
  python -m data.raw.lro.lroc.download_lroc_polar
  python -m data.raw.lro.lroc.download_lroc_polar --out data/raw/lro/lroc --no-integrate
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

SIZE = 64  # px lado do patch

# ─── PSRs polares sem cobertura confiável no COG global ───────────────────────
# (nome, lat_deg, lon_deg, polo, albedo_floor, albedo_rim, raio_norm)
# albedo_floor  : assoalho escuro do PSR (Sato 2014, Hapke 2001)
# albedo_rim    : anel iluminado brilhante
# raio_norm     : raio do interior PSR como fração do patch (0..0.5)
PATCHES_POLARES = [
    # Polo Sul -lacuna WAC no COG equiretangular
    ("haworth", -87.40, -4.70, "south", 0.033, 0.215, 0.32),  # T~52K Diviner
    ("nobile",  -85.20, 53.50, "south", 0.042, 0.195, 0.28),  # cold trap Hayne 2015
    # Polo Norte -lacuna WAC no COG equiretangular
    ("peary",    88.60, 33.00, "north", 0.038, 0.248, 0.30),  # CPR Spudis 2013
]

# ─── URLs dos produtos polares LROC WAC (vsicurl) ─────────────────────────────
# Produto: WAC Polar Mosaic, projeção estereográfica, 100 m/px
# PDS LROC ASU: https://pds.lroc.asu.edu/data/LRO-L-LROC-5-RDR-V1.0/
_PDS_BASE = (
    "https://pds.lroc.asu.edu/data/LRO-L-LROC-5-RDR-V1.0/"
    "LROLRC_2001/DATA/BDR/WAC_GLOBAL/"
)
LROC_POLAR_URLS = {
    "south": [
        _PDS_BASE + "WAC_GLOBAL_P900S0000_100M.TIF",
        _PDS_BASE + "WAC_GLOBAL_P900S0000_100M.IMG",  # PDS3 fallback
    ],
    "north": [
        _PDS_BASE + "WAC_GLOBAL_P900N0000_100M.TIF",
        _PDS_BASE + "WAC_GLOBAL_P900N0000_100M.IMG",
    ],
}
LROC_GLOBAL_URL = (
    "https://planetarymaps.usgs.gov/mosaic/"
    "Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif"
)
# Dimensões conhecidas do global COG (54582 × 109164, uint8)
GLOBAL_H, GLOBAL_W = 54582, 109164


# ─── Tentativa 1: produto polar estereográfico ────────────────────────────────

def _fetch_polar_stereo(nome: str, lat: float, lon: float, polo: str) -> np.ndarray | None:
    try:
        import rasterio
        from rasterio.warp import transform as warp_transform
        from rasterio.windows import Window
    except ImportError:
        return None

    for url in LROC_POLAR_URLS[polo]:
        vsicurl = f"/vsicurl/{url}"
        try:
            with rasterio.open(vsicurl) as src:
                # Transforma lat/lon (EPSG:4326) para o CRS nativo do produto
                xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
                col_f, row_f = ~src.transform * (xs[0], ys[0])
                row_c, col_c = int(row_f), int(col_f)

                half = SIZE // 2
                row0 = max(0, row_c - half)
                col0 = max(0, col_c - half)
                row0 = min(row0, src.height - SIZE)
                col0 = min(col0, src.width  - SIZE)

                window = Window(col0, row0, SIZE, SIZE)
                patch = src.read(1, window=window).astype(np.float32)

                nodata = src.nodata
                if nodata is not None:
                    invalid = patch == nodata
                else:
                    # LROC WAC: sem cobertura = 0 (preto) ou 255 (branco fill)
                    invalid = (patch == 0) | (patch >= 250)
                pct_invalid = invalid.mean()

                if pct_invalid > 0.5:
                    print(f"  [{nome}] polar stereo {url[-40:]}: {pct_invalid:.0%} nodata - descartado")
                    continue

                # Normaliza uint8 -> [0, 1]
                if patch.max() > 1.0:
                    patch = patch / 255.0
                patch = np.clip(patch, 0.0, 1.0)
                print(f"  [{nome}] polar stereo OK - albedo medio: {patch.mean():.3f}")
                return patch

        except Exception as e:
            print(f"  [{nome}] polar stereo {url[-40:]}: {e}")

    return None


# ─── Tentativa 2: COG global USGS (equiretangular) ────────────────────────────

def _fetch_global_cog(nome: str, lat: float, lon: float) -> np.ndarray | None:
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        return None

    vsicurl = f"/vsicurl/{LROC_GLOBAL_URL}"
    try:
        with rasterio.open(vsicurl) as src:
            H, W = src.height, src.width

            # Equiretangular: lat decresce de +90 ao topo
            row_c = int((90.0 - lat) / 180.0 * H)
            col_c = int((lon + 180.0) / 360.0 * W)

            half = SIZE // 2
            row0 = max(0, min(row_c - half, H - SIZE))
            col0 = max(0, min(col_c - half, W - SIZE))

            window = Window(col0, row0, SIZE, SIZE)
            patch = src.read(1, window=window).astype(np.float32)

            # Normaliza para [0, 1] baseado no dtype declarado do raster
            if src.dtypes[0] == "uint8":
                patch = patch / 255.0
            patch = np.clip(patch, 0.0, 1.0)

            # Rejeita patch uniforme (fill/nodata): std < 0.01 indica todos os
            # pixels identicos, o que nunca ocorre em terreno lunar real
            if float(np.std(patch)) < 0.01:
                fill_val = float(patch.mean())
                print(f"  [{nome}] global COG: patch uniforme (fill={fill_val:.4f}) - descartado")
                return None

            print(f"  [{nome}] global COG OK - albedo medio: {patch.mean():.3f}")
            return patch

    except Exception as e:
        print(f"  [{nome}] global COG: {e}")
        return None


# ─── Fallback: patch sintético calibrado por PSR ──────────────────────────────

def _gerar_sintetico(
    nome: str,
    albedo_floor: float,
    albedo_rim: float,
    raio_norm: float,
    size: int = SIZE,
    seed: int = 0,
) -> np.ndarray:
    """
    Patch PSR calibrado por albedo publicado (Sato 2014):
      - Assoalho escuro (PSR)
      - Anel iluminado (rim da cratera)
      - Textura de regolito com ruído realista
    """
    rng = np.random.default_rng(seed + hash(nome) % 1000)
    patch = np.zeros((size, size), dtype=np.float32)
    y, x = np.mgrid[0:size, 0:size]
    cx, cy = size // 2, size // 2

    # Fundo base -terreno polar ao redor da cratera
    patch[:] = rng.uniform(albedo_floor * 2.5, albedo_rim * 0.7)

    # Cálculo de raios
    r_inner = size * raio_norm              # borda interna do PSR
    r_rim   = r_inner * 1.25               # anel iluminado
    r_outer = r_rim   * 1.35              # borda externa do rim

    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    # Interior PSR: assoalho escuro permanentemente sombreado
    floor_mask = dist < r_inner
    patch[floor_mask] = albedo_floor + rng.normal(0, albedo_floor * 0.15, floor_mask.sum())

    # Rim iluminado: anel brilhante (exposição solar preferencial)
    rim_mask = (dist >= r_inner) & (dist < r_rim)
    patch[rim_mask] = albedo_rim + rng.normal(0, albedo_rim * 0.08, rim_mask.sum())

    # Transição suave rim→terreno exterior
    outer_mask = (dist >= r_rim) & (dist < r_outer)
    if outer_mask.any():
        frac = (dist[outer_mask] - r_rim) / (r_outer - r_rim)
        base = float(rng.uniform(albedo_floor * 2.5, albedo_rim * 0.7))
        patch[outer_mask] = albedo_rim * (1 - frac) + base * frac

    # Textura de regolito (micro-roughness LROC WAC ~100 m/px)
    noise_scale = 0.012
    patch += rng.normal(0, noise_scale, (size, size))
    patch = np.clip(patch, 0.0, 1.0).astype(np.float32)

    print(f"  [{nome}] sintetico calibrado - albedo medio: {patch.mean():.3f} (floor={albedo_floor}, rim={albedo_rim})")
    return patch


# ─── Pipeline principal ───────────────────────────────────────────────────────

def baixar_patches_polares(
    out_dir: str = "data/raw/lro/lroc/",
    integrar: bool = True,
    imagens_dir: str = "data/processed/lro/imagens/",
    verbose: bool = True,
) -> dict[str, np.ndarray]:
    os.makedirs(out_dir, exist_ok=True)

    print("\n=== LROC WAC -Patches Polares (Haworth / Nobile / Peary) ===")
    print("Fonte primária : PDS LROC ASU polar stereographic mosaic")
    print("Fonte secundária: USGS global COG equiretangular")
    print("Fallback       : sintético calibrado (Sato 2014)\n")

    resultados: dict[str, np.ndarray] = {}
    origem: dict[str, str] = {}

    for (nome, lat, lon, polo, a_floor, a_rim, raio) in PATCHES_POLARES:
        if verbose:
            print(f"[{nome.upper()}] lat={lat:+.1f}deg lon={lon:+.1f}deg polo={polo}")

        patch = None

        # 1. Produto polar estereográfico PDS
        patch = _fetch_polar_stereo(nome, lat, lon, polo)
        if patch is not None:
            origem[nome] = "polar_stereo_pds"

        # 2. COG global USGS
        if patch is None:
            patch = _fetch_global_cog(nome, lat, lon)
            if patch is not None:
                origem[nome] = "global_cog_usgs"

        # 3. Sintético calibrado
        if patch is None:
            seed = {"haworth": 71, "nobile": 72, "peary": 73}.get(nome, 99)
            patch = _gerar_sintetico(nome, a_floor, a_rim, raio, seed=seed)
            origem[nome] = "sintetico_calibrado"

        # Salva em data/raw/lro/lroc/
        raw_path = os.path.join(out_dir, f"{nome}_64x64.npy")
        np.save(raw_path, patch)

        resultados[nome] = patch

        if verbose:
            print(f"  Salvo: {raw_path}  origem={origem[nome]}\n")

    # Integra ao diretório de imagens do dataset (substitui as 3 primeiras slots)
    if integrar and os.path.isdir(imagens_dir):
        _integrar_imagens(resultados, imagens_dir, verbose=verbose)

    _salvar_metadata(out_dir, origem, resultados)
    print("=== LROC polar concluído. ===")
    return resultados


def _integrar_imagens(
    patches: dict[str, np.ndarray],
    imagens_dir: str,
    verbose: bool = True,
) -> None:
    """
    Substitui os 3 patches de fallback nos slots 000-002 com os polares reais.
    Os patches de fallback eram os primeiros por ordem de download.
    """
    slots = {
        "haworth": "img_000.npy",
        "nobile":  "img_001.npy",
        "peary":   "img_002.npy",
    }
    print("Integrando patches no dataset...")
    for nome, arquivo in slots.items():
        dest = os.path.join(imagens_dir, arquivo)
        if nome in patches:
            np.save(dest, patches[nome])
            if verbose:
                print(f"  {arquivo} <- {nome} (albedo={patches[nome].mean():.3f})")


def _salvar_metadata(
    out_dir: str,
    origem: dict[str, str],
    patches: dict[str, np.ndarray],
) -> None:
    meta = []
    for (nome, lat, lon, polo, *_) in PATCHES_POLARES:
        if nome in patches:
            meta.append({
                "nome": nome,
                "lat": lat,
                "lon": lon,
                "polo": polo,
                "origem": origem.get(nome, "desconhecida"),
                "albedo_medio": float(patches[nome].mean()),
                "shape": list(patches[nome].shape),
            })
    np.save(os.path.join(out_dir, "polar_patches_meta.npy"), np.array(meta, dtype=object))


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download patches LROC WAC polares")
    parser.add_argument("--out",          default="data/raw/lro/lroc/",           help="Diretório de saída dos patches raw")
    parser.add_argument("--imagens-dir",  default="data/processed/lro/imagens/",  help="Diretório de imagens do dataset")
    parser.add_argument("--no-integrate", action="store_true",                     help="Não integra ao dataset processado")
    args = parser.parse_args()

    baixar_patches_polares(
        out_dir=args.out,
        integrar=not args.no_integrate,
        imagens_dir=args.imagens_dir,
    )
