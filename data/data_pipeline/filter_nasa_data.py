"""
Carregamento seletivo de dados NASA LRO por streaming de janelas espaciais.

Processa arquivos grandes (3+ GB) sem carregar tudo na RAM.
Filtra apenas pixels relevantes: regiões polares com temperatura < 110K.

Uso:
    python -m data.data_pipeline.filter_nasa_data
    python -m data.data_pipeline.filter_nasa_data --lat-min 70 --temp-max 150
"""

import argparse
import os

import numpy as np
import rasterio
from rasterio.windows import Window

# ─── Constantes ───────────────────────────────────────────────────────────────
TEMP_ICE_STABLE = 110.0   # K — Zhang & Paige (2009)
SOLAR_CONSTANT  = 1361.0  # W/m²

RAW_DIVINER  = "data/raw/lro/diviner/dghrm_tbol_m_70s70n_geotiff.tif"
RAW_LOLA     = "data/raw/lro/illumination/ldec_4.img"
OUT_DIR      = "data/processed/lro/"

CHUNK_ROWS   = 256   # linhas por janela — ajuste conforme RAM disponível


# ─── Loader por janelas (streaming) ───────────────────────────────────────────

def filtrar_diviner(
    tif_path: str,
    out_dir: str,
    lat_min: float = 70.0,
    temp_max: float = TEMP_ICE_STABLE,
    chunk_rows: int = CHUNK_ROWS,
    verbose: bool = True,
) -> np.ndarray:
    """
    Lê o GeoTIFF do Diviner em chunks e salva apenas os pixels onde:
      abs(lat) >= lat_min  AND  temp <= temp_max

    Retorna array (H_filtrado, W) com os dados relevantes.
    Não carrega o arquivo inteiro na RAM em nenhum momento.
    """
    if not os.path.exists(tif_path):
        raise FileNotFoundError(
            f"Arquivo não encontrado: {tif_path}\n"
            f"Baixe em: https://pds-geosciences.wustl.edu/lro/"
            f"urn-nasa-pds-lro_diviner_derived1/data_derived_ghrm/geotiff/"
            f"dghrm_tbol_m_70s70n_geotiff.tif"
        )

    os.makedirs(out_dir, exist_ok=True)

    with rasterio.open(tif_path) as src:
        H, W = src.height, src.width
        transform = src.transform
        nodata = src.nodata

        if verbose:
            print(f"Diviner GeoTIFF: {H}x{W} pixels")
            print(f"  Resolucao: {abs(transform.a):.4f} deg/pixel")
            print(f"  Filtro: |lat| >= {lat_min} deg  AND  T <= {temp_max} K")
            print(f"  Chunk: {chunk_rows} linhas por vez\n")

        linhas_relevantes = []
        lats_relevantes   = []
        total_pixels = 0
        chunks_lidos = 0

        for row_off in range(0, H, chunk_rows):
            rows_neste_chunk = min(chunk_rows, H - row_off)
            window = Window(0, row_off, W, rows_neste_chunk)

            chunk = src.read(1, window=window).astype(np.float32)

            # Remove nodata
            if nodata is not None:
                chunk[chunk == nodata] = np.nan

            # Latitude de cada linha neste chunk
            lats = np.array([
                transform.f + (row_off + r + 0.5) * transform.e
                for r in range(rows_neste_chunk)
            ])

            # Máscara: lat polar E temperatura abaixo do limiar
            mask_lat  = np.abs(lats) >= lat_min
            mask_temp = np.nanmin(chunk, axis=1) <= temp_max
            mask = mask_lat & mask_temp

            if mask.any():
                linhas_relevantes.append(chunk[mask])
                lats_relevantes.extend(lats[mask].tolist())
                total_pixels += mask.sum() * W

            chunks_lidos += 1
            if verbose and chunks_lidos % 10 == 0:
                pct = 100 * row_off / H
                print(f"  {pct:.0f}% processado ({row_off}/{H} linhas)...", end="\r")

    if verbose:
        print(f"\n  100% concluido")

    if not linhas_relevantes:
        print("Nenhum pixel relevante encontrado com os filtros aplicados.")
        return np.array([])

    dados = np.vstack(linhas_relevantes).astype(np.float32)
    lats_arr = np.array(lats_relevantes, dtype=np.float32)

    # Normaliza para 0-1 (remove NaN antes)
    dados_clean = np.nan_to_num(dados, nan=0.0)
    if dados_clean.max() > dados_clean.min():
        dados_norm = (dados_clean - dados_clean.min()) / (dados_clean.max() - dados_clean.min())
    else:
        dados_norm = dados_clean

    # Salva resultado filtrado
    np.save(os.path.join(out_dir, "temperatura.npy"), dados_norm)
    np.save(os.path.join(out_dir, "temperatura_raw_K.npy"), dados_clean)
    np.save(os.path.join(out_dir, "temperatura_lats.npy"), lats_arr)

    if verbose:
        print(f"\nResultado filtrado:")
        print(f"  Shape: {dados_norm.shape}")
        print(f"  Temp min: {dados_clean[dados_clean > 0].min():.1f} K")
        print(f"  Temp max: {dados_clean.max():.1f} K")
        print(f"  Pixels PSR relevantes: {total_pixels:,}")
        print(f"  Salvo em: {out_dir}temperatura.npy")

    return dados_norm


def filtrar_lola_iluminacao(
    img_path: str,
    out_dir: str,
    lat_min: float = 70.0,
    verbose: bool = True,
) -> np.ndarray:
    """
    Lê o mapa LOLA de iluminação (formato IMG binário, 4 ppd).
    Arquivo pequeno (2 MB) — leitura direta sem streaming.

    Referência: Mazarico et al. (2011) Icarus 211, 1066
    """
    if not os.path.exists(img_path):
        raise FileNotFoundError(
            f"Arquivo não encontrado: {img_path}\n"
            f"Baixe em: https://pds-geosciences.wustl.edu/lro/"
            f"lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldec_4.img"
        )

    os.makedirs(out_dir, exist_ok=True)

    with rasterio.open(img_path) as src:
        arr = src.read(1).astype(np.float32)
        H, W = arr.shape
        transform = src.transform

        if verbose:
            print(f"LOLA IMG: {H}x{W} pixels ({abs(transform.a):.2f} deg/pixel)")

    # LOLA 4ppd: 720 linhas × 1440 colunas
    # Linha 0 = 90°N, linha 719 = 90°S
    lat_vals = np.linspace(90, -90, H, endpoint=False) - (90 / H)
    mask = np.abs(lat_vals) >= lat_min

    arr_polar = arr[mask]
    lats_polar = lat_vals[mask]

    # Converte fracao de iluminacao para W/m²
    arr_polar_wm2 = np.clip(arr_polar, 0, 1) * SOLAR_CONSTANT

    # Reamostrar para grade 180x360 (1 grau/px) que o dataset espera.
    # LOLA 4ppd: 720 linhas x 1440 colunas -> 4 pixels por grau em cada eixo.
    # Media de blocos 4x4 para obter 1 grau/px.
    H_out, W_out = 180, 360
    # Grade completa com valor equatorial padrao
    grade = np.full((H_out, W_out), 500.0, dtype=np.float32)

    H_src, W_src = arr.shape
    bh = H_src // H_out   # 720/180 = 4
    bw = W_src // W_out   # 1440/360 = 4

    for i in range(H_out):
        r0, r1 = i * bh, (i + 1) * bh
        lat_i = 90.0 - (i + 0.5) * (180.0 / H_out)
        if abs(lat_i) >= lat_min:
            bloco = arr[r0:r1, :]   # (bh, W_src)
            bloco_wm2 = np.clip(bloco, 0, 1) * SOLAR_CONSTANT
            # Agrupa colunas em W_out blocos de bw
            bloco_360 = bloco_wm2.reshape(bh, W_out, bw).mean(axis=(0, 2))
            grade[i, :] = bloco_360

    np.save(os.path.join(out_dir, "insolacao.npy"), grade)
    # Mantem arquivo auxiliar com dados polares brutos para uso diagnostico
    np.save(os.path.join(out_dir, "insolacao_polar_raw.npy"), arr_polar_wm2.astype(np.float32))
    np.save(os.path.join(out_dir, "insolacao_lats.npy"), lats_polar.astype(np.float32))

    if verbose:
        polar_vals = grade[np.abs(np.linspace(-89.5, 89.5, H_out)) >= lat_min]
        print(f"  Grade (180x360): min={grade.min():.1f}  max={grade.max():.1f} W/m2")
        print(f"  Polar (|lat|>={lat_min}): {polar_vals.size} pixels")
        print(f"  Salvo em: {out_dir}insolacao.npy")

    return grade


# ─── Pipeline completo ────────────────────────────────────────────────────────

def pipeline_completo(lat_min=70.0, temp_max=TEMP_ICE_STABLE, out_dir=OUT_DIR):
    print("=" * 60)
    print("PIPELINE NASA LRO — FILTRAGEM SELETIVA DE PSRs")
    print("=" * 60)

    erros = []

    print("\n[1/2] Diviner temperatura...")
    try:
        filtrar_diviner(RAW_DIVINER, out_dir, lat_min=lat_min, temp_max=temp_max)
    except FileNotFoundError as e:
        print(f"  AVISO: {e}")
        erros.append("diviner")

    print("\n[2/2] LOLA iluminacao...")
    try:
        filtrar_lola_iluminacao(RAW_LOLA, out_dir, lat_min=lat_min)
    except FileNotFoundError as e:
        print(f"  AVISO: {e}")
        erros.append("lola")

    if erros:
        print(f"\nArquivos em falta: {erros}")
        print("Baixe os arquivos e rode novamente.")
        print("Use DATA_MODE=mock enquanto isso.")
    else:
        print("\nPipeline concluido. Rode o backend com DATA_MODE=real")

    return len(erros) == 0


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filtra dados NASA LRO por PSR")
    parser.add_argument("--lat-min",  type=float, default=70.0,  help="Latitude minima (graus)")
    parser.add_argument("--temp-max", type=float, default=110.0, help="Temperatura maxima (K)")
    parser.add_argument("--out",      default=OUT_DIR,           help="Diretorio de saida")
    parser.add_argument("--diviner-only", action="store_true")
    parser.add_argument("--lola-only",    action="store_true")
    args = parser.parse_args()

    if args.diviner_only:
        filtrar_diviner(RAW_DIVINER, args.out, args.lat_min, args.temp_max)
    elif args.lola_only:
        filtrar_lola_iluminacao(RAW_LOLA, args.out, args.lat_min)
    else:
        pipeline_completo(args.lat_min, args.temp_max, args.out)
