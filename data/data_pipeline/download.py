"""
Download de dados NASA LRO — ponto de entrada unificado.

Delega para os scripts especializados:
  - Diviner (temperatura PSR): data/raw/lro/diviner/download_diviner.py
  - LOLA (iluminação):         data/data_pipeline/filter_nasa_data.py
  - LAMP (UV gelo):            data/raw/lro/lamp/parse_lamp.py

Uso:
  python -m data.data_pipeline.download --diviner-epf
  python -m data.data_pipeline.download --lamp
  python -m data.data_pipeline.download --lola-stream
  python -m data.data_pipeline.download --tudo
"""

import argparse
import os
import urllib.request


def baixar_arquivo(url: str, destino: str, desc: str = "") -> bool:
    """Download com suporte a range requests e cache local."""
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        print(f"  [cache] {desc or os.path.basename(destino)}")
        return True

    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    print(f"  Baixando {desc or url}...", end=" ", flush=True)
    try:
        urllib.request.urlretrieve(url, destino)
        kb = os.path.getsize(destino) // 1024
        print(f"OK ({kb} KB)")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        return False


def baixar_diviner_epf():
    """Temperaturas reais de PSRs polares via Diviner EPF (~15 MB total)."""
    from data.raw.lro.diviner.download_diviner import baixar_diviner_epf as _run
    _run()


def baixar_lamp():
    """Dados UV LAMP para assinatura de gelo (~10 MB)."""
    from data.raw.lro.lamp.parse_lamp import pipeline_lamp
    pipeline_lamp()


def baixar_lroc_polar(out_dir: str = "data/raw/lro/lroc/", integrar: bool = True):
    """Patches LROC WAC para PSRs polares (Haworth/Nobile/Peary) — PDS polar + fallback sintético."""
    from data.raw.lro.lroc.download_lroc_polar import baixar_patches_polares
    baixar_patches_polares(out_dir=out_dir, integrar=integrar)


def baixar_lola_stream(lat_min: float = 60.0):
    """
    Streaming seletivo do Diviner GeoTIFF via vsicurl.
    Lê apenas faixas polares (|lat| >= lat_min) sem baixar os 3.3 GB inteiros.
    """
    from data.data_pipeline.filter_nasa_data import pipeline_completo
    pipeline_completo(lat_min=lat_min)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download dados NASA LRO")
    parser.add_argument("--diviner-epf",  action="store_true", help="Diviner EPF PSRs (~15 MB)")
    parser.add_argument("--lamp",         action="store_true", help="LAMP UV gelo (~10 MB)")
    parser.add_argument("--lola-stream",  action="store_true", help="Diviner polar via vsicurl")
    parser.add_argument("--lroc-polar",   action="store_true", help="Patches LROC WAC polares (Haworth/Nobile/Peary)")
    parser.add_argument("--lat-min",      type=float, default=60.0)
    parser.add_argument("--tudo",         action="store_true", help="Todos os datasets pequenos")
    args = parser.parse_args()

    if args.tudo:
        args.diviner_epf = True
        args.lamp = True
        args.lroc_polar = True

    if args.diviner_epf:
        print("\n=== Diviner EPF ===")
        baixar_diviner_epf()

    if args.lamp:
        print("\n=== LAMP UV ===")
        baixar_lamp()

    if args.lola_stream:
        print("\n=== LOLA/Diviner stream polar ===")
        baixar_lola_stream(lat_min=args.lat_min)

    if args.lroc_polar:
        print("\n=== LROC WAC Patches Polares ===")
        baixar_lroc_polar()

    if not any([args.diviner_epf, args.lamp, args.lola_stream, args.lroc_polar, args.tudo]):
        parser.print_help()
