"""
Download de dados reais do instrumento Diviner (LRO).

O dataset completo Diviner está no PDS da NASA:
  https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/

Os arquivos GeoTIFF globais (dghrm_tbol) têm ~3.3 GB cada.
Este script baixa o produto mais compacto disponível: EPF (Effect Phase Function)
para crateras polares específicas — mas "compacto" é relativo ao GeoTIFF global,
não em termos absolutos. Verificado em 2026-08-20: o CSV do Cabeus
("1917_Cabeus_EPF_alltargeted.csv.zip") tem ~2.7 GB comprimido e descompacta
pra ~14 GB — não são "poucos MB" como o comentário antigo dizia. As outras
crateras (Nobile/Amundsen/VIPER) não foram testadas, tamanho pode variar.
`processar_epf_csv()` já reduz isso pra um `.npy` pequeno (só as temperaturas
válidas), então o CSV/zip brutos servem só como cache intermediário —
seguro apagar depois de gerar os artefatos processados (`labels_gelo.npy`
via `generate_labels.py`, `diviner_epf_<cratera>.npy` daqui), rebaixando
depois se precisar reprocessar do zero.

Referência: Paige et al. (2010) Science 330, 479
            Williams et al. (2019) JGR Planets — Diviner EPF dataset
"""

import csv
import os
import sys
import urllib.request
import zipfile

import numpy as np

EPF_BASE = (
    "https://pds-geosciences.wustl.edu/lro/"
    "urn-nasa-pds-lro_diviner_derived2/data_derived_epf/"
)

# Nomes reais no PDS (verificados via collection_data_derived_epf_inventory.csv)
EPF_CRATERAS = {
    "Cabeus":    "1917_Cabeus_EPF_alltargeted.csv.zip",    # gelo LCROSS 2009
    "Nobile":    "1906_Nobile_2_EPF_alltargeted.csv.zip",  # PSR polo sul
    "Amundsen":  "1921_Amundsen_PSR_alltargeted.csv.zip",  # PSR polo sul
    "VIPER":     "1900_VIPER_EPF_target_alltargeted.csv.zip",  # polo sul
}

DOC_URL = (
    "https://pds-geosciences.wustl.edu/lro/"
    "urn-nasa-pds-lro_diviner_derived1/document/Diviner_RDR_SIS.pdf"
)


def download_arquivo(url: str, destino: str, desc: str = "") -> bool:
    if os.path.exists(destino):
        print(f"  [cache] {desc or os.path.basename(destino)}")
        return True

    os.makedirs(os.path.dirname(destino), exist_ok=True)
    print(f"  Baixando {desc or url} ...", end=" ", flush=True)
    try:
        urllib.request.urlretrieve(url, destino)
        size_kb = os.path.getsize(destino) / 1024
        print(f"OK ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        if os.path.exists(destino):
            os.remove(destino)
        return False


def processar_epf_csv(csv_path: str, out_dir: str, nome: str) -> dict:
    temps = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                t = float(row.get("T_LUNAR") or row.get("TEMP") or 0)
                if 20 < t < 450:
                    temps.append(t)
            except (ValueError, KeyError):
                continue

    if not temps:
        return {}

    arr = np.array(temps, dtype=np.float32)
    np.save(os.path.join(out_dir, f"diviner_epf_{nome.lower()}.npy"), arr)
    stats = {
        "cratera": nome,
        "n_medidas": len(arr),
        "T_min_K": float(arr.min()),
        "T_max_K": float(arr.max()),
        "T_media_K": float(arr.mean()),
    }
    print(f"  {nome}: {len(arr)} medidas, T_media={arr.mean():.1f}K, T_min={arr.min():.1f}K")
    return stats


def baixar_diviner_epf(out_dir: str = "data/raw/lro/diviner/") -> None:
    os.makedirs(out_dir, exist_ok=True)

    print("\n=== Diviner EPF — PSR Temperature Data ===")
    print("Fonte: PDS-Geosciences WUSTL (Williams et al. 2019)\n")

    stats_totais = []

    for nome, arquivo in EPF_CRATERAS.items():
        url = EPF_BASE + arquivo
        zip_path = os.path.join(out_dir, arquivo)
        csv_path = zip_path.replace(".zip", "")

        if not download_arquivo(url, zip_path, f"Diviner EPF {nome}"):
            continue

        if not os.path.exists(csv_path):
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(out_dir)
            except Exception as e:
                print(f"  Erro ao extrair {zip_path}: {e}")
                continue

        if os.path.exists(csv_path):
            stats = processar_epf_csv(csv_path, out_dir, nome)
            if stats:
                stats_totais.append(stats)

    if stats_totais:
        np.save(os.path.join(out_dir, "diviner_psr_summary.npy"), np.array(stats_totais, dtype=object))

    download_arquivo(DOC_URL, os.path.join(out_dir, "Diviner_RDR_SIS.pdf"), "Diviner SIS (documentação)")
    print("\nDiviner EPF concluído.")


def print_info_global() -> None:
    print("""
=== Diviner Global Temperature Map (dataset completo) ===
URL: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_ghrm/geotiff/
Arquivo: dghrm_tbol_m_70s70n_geotiff.tif (~3.3 GB)

Para baixar (requer ~10 GB de espaço):
  wget <URL_acima>

Após download, coloque em data/raw/lro/diviner/ e rode clean_nasa_data.py
""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download dados Diviner LRO")
    parser.add_argument("--epf", action="store_true", help="Baixa EPF de PSRs (~15 MB)")
    parser.add_argument("--info", action="store_true", help="Info sobre dataset global")
    parser.add_argument("--out", default="data/raw/lro/diviner/")
    args = parser.parse_args()

    if args.info:
        print_info_global()
    if args.epf:
        baixar_diviner_epf(args.out)
    if not args.epf and not args.info:
        print("Uso: python download_diviner.py --epf   # baixa EPF de PSRs")
        print("     python download_diviner.py --info  # info do dataset global")
