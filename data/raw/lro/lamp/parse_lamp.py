"""
Parser de dados LAMP (Lyman Alpha Mapping Project) do LRO.

LAMP detecta H2O exposto em PSRs via emissão UV de Lyman-alpha (121.6 nm).
Assinatura de gelo: menor albedo UV do que solo seco (~1360 Angstrom).

Refs:
  Gladstone et al. (2010) Science 330 — LAMP detecta gelo em Shackleton
  Hayne et al. (2015) JGR — mapa global de hidratação superficial

Formato: FITS padrão astronômico
  HDU 0: imagem ou dados espectrais
  HDU 1+: tabelas de eventos

Download (sem autenticação):
  https://planetarydata.jpl.nasa.gov/img/data/lro/lro_lamp/rdr/LROLAM_1025/DATA/2015258/
"""

import os
import urllib.request
import numpy as np

try:
    from astropy.io import fits
    ASTROPY_OK = True
except ImportError:
    ASTROPY_OK = False
    print("astropy nao instalado. Rode: pip install astropy")


LAMP_URLS = {
    "2015_258_a": (
        "https://planetarydata.jpl.nasa.gov/img/data/lro/lro_lamp/rdr/"
        "LROLAM_1025/DATA/2015258/LAMP_SCI_0464051390_03.fit",
        4_900_000,
    ),
    "2015_258_b": (
        "https://planetarydata.jpl.nasa.gov/img/data/lro/lro_lamp/rdr/"
        "LROLAM_1025/DATA/2015258/LAMP_SCI_0464053202_03.fit",
        4_800_000,
    ),
}


def baixar_lamp(out_dir: str = "data/raw/lro/lamp/") -> list:
    os.makedirs(out_dir, exist_ok=True)
    baixados = []

    for nome, (url, tamanho_aprox) in LAMP_URLS.items():
        destino = os.path.join(out_dir, f"{nome}.fit")
        if os.path.exists(destino):
            print(f"  [cache] {nome}.fit")
            baixados.append(destino)
            continue

        print(f"  Baixando {nome} (~{tamanho_aprox//1000} KB)...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, destino)
            print(f"OK ({os.path.getsize(destino)//1024} KB)")
            baixados.append(destino)
        except Exception as e:
            print(f"ERRO: {e}")

    return baixados


def parsear_fits(path: str, verbose: bool = True) -> dict:
    if not ASTROPY_OK:
        raise ImportError("astropy necessario: pip install astropy")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    resultado = {}

    with fits.open(path, memmap=True) as hdul:
        if verbose:
            print(f"\nFITS: {os.path.basename(path)}")
            hdul.info()

        for i, hdu in enumerate(hdul):
            nome_hdu = hdu.name or f"HDU{i}"

            if isinstance(hdu, fits.PrimaryHDU) and hdu.data is not None:
                img = np.array(hdu.data, dtype=np.float32)
                resultado["imagem"] = img
                # PRIMARY e uma imagem espectral (linhas espaciais x bins de comprimento de onda)
                # Usa soma por linha como proxy de contagem total UV por pixel espacial
                if img.ndim == 2:
                    resultado["counts"] = img.sum(axis=1)
                if verbose:
                    print(f"  {nome_hdu}: shape={hdu.data.shape} dtype={hdu.data.dtype}")

            elif isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                cols = hdu.columns.names
                if verbose:
                    print(f"  {nome_hdu}: {len(hdu.data)} linhas | colunas={cols[:5]}...")

                # Extrai colunas relevantes para detecção de gelo
                tabela = {}
                for col in cols:
                    try:
                        tabela[col] = np.array(hdu.data[col])
                    except Exception:
                        pass

                resultado[f"tabela_{nome_hdu}"] = tabela

                # Extrai taxa de contagem UV (assinatura de gelo = COUNT_RATE baixo)
                # Nomes de coluna variam por versao do produto LAMP
                count_candidates = ["COUNTS", "SIGNAL", "COUNT_RATE", "RATE"]
                for cname in count_candidates:
                    if cname in cols:
                        counts = np.array(hdu.data[cname], dtype=np.float32)
                        resultado["counts"] = counts
                        if verbose:
                            print(f"  UV {cname}: min={counts.min():.2f} max={counts.max():.2f} mean={counts.mean():.2f}")
                        break

    return resultado


def extrair_assinatura_gelo(fits_data: dict, threshold_percentil: float = 20.0) -> np.ndarray | None:
    """
    Pixels com albedo UV abaixo do percentil indicado sugerem gelo exposto.
    Ref: Hayne et al. (2015) — gelo tem menor albedo UV que regolito seco.
    """
    if "counts" not in fits_data:
        return None

    counts = fits_data["counts"]
    limiar = np.percentile(counts, threshold_percentil)
    mascara_gelo = (counts < limiar).astype(np.float32)
    return mascara_gelo


def pipeline_lamp(out_dir: str = "data/raw/lro/lamp/") -> dict:
    print("=== LAMP UV Pipeline ===")

    arquivos = baixar_lamp(out_dir)
    if not arquivos:
        print("Nenhum arquivo LAMP baixado.")
        return {}

    resultados = {}
    for path in arquivos:
        try:
            dados = parsear_fits(path)
            gelo  = extrair_assinatura_gelo(dados)
            if gelo is not None:
                nome = os.path.splitext(os.path.basename(path))[0]
                np.save(os.path.join(out_dir, f"{nome}_gelo_mask.npy"), gelo)
                resultados[nome] = {
                    "gelo_pixels": int(gelo.sum()),
                    "total_pixels": int(gelo.size),
                    "pct_gelo": float(gelo.mean() * 100),
                }
                print(f"  {nome}: {resultados[nome]['pct_gelo']:.1f}% pixels com assinatura de gelo")
        except Exception as e:
            print(f"  Erro em {path}: {e}")

    return resultados


if __name__ == "__main__":
    pipeline_lamp()
