import os
import numpy as np
import rasterio

# =========================
# 📁 DIRETÓRIOS
# =========================

RAW_DIR = "data/raw/lro/"
INTERIM_DIR = "data/interim/lro/cleaned/"

os.makedirs(INTERIM_DIR, exist_ok=True)


# =========================
# 🧠 UTIL: LIMPEZA GERAL
# =========================

def limpar_array(arr, clip_min=None, clip_max=None):
    """
    Limpa dados científicos:
    - remove NaN/inf
    - aplica clipping físico
    - normaliza (0–1)
    """

    arr = arr.astype(np.float32)

    # remover valores inválidos
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    # clipping físico (se fornecido)
    if clip_min is not None:
        arr[arr < clip_min] = clip_min

    if clip_max is not None:
        arr[arr > clip_max] = clip_max

    # normalização
    if arr.max() > 0:
        arr = arr / arr.max()

    return arr


# =========================
# 📡 CARREGAR GEO TIFF
# =========================

def carregar_geotiff(caminho):
    with rasterio.open(caminho) as src:
        arr = src.read(1)
        meta = {
            "bounds": src.bounds,
            "transform": src.transform,
            "crs": str(src.crs)
        }

    return arr, meta


# =========================
# 🌡️ LIMPAR TEMPERATURA (DIVINER)
# =========================

def limpar_temperatura():

    pasta = os.path.join(RAW_DIR, "diviner")
    arquivos = [f for f in os.listdir(pasta) if f.endswith(".tif")]

    if not arquivos:
        raise Exception("❌ Nenhum arquivo Diviner encontrado")

    caminho = os.path.join(pasta, arquivos[0])

    print("📡 Limpando temperatura:", caminho)

    arr, meta = carregar_geotiff(caminho)

    # temperatura lunar típica: ~40K a 400K
    arr = limpar_array(arr, clip_min=40, clip_max=400)

    np.save(os.path.join(INTERIM_DIR, "temperatura_clean.npy"), arr)
    np.save(os.path.join(INTERIM_DIR, "temperatura_meta.npy"), meta)

    print("✅ temperatura_clean.npy salvo")


# =========================
# 🌞 LIMPAR INSOLAÇÃO
# =========================

def limpar_insolacao():

    pasta = os.path.join(RAW_DIR, "illumination")
    arquivos = [f for f in os.listdir(pasta) if f.endswith(".tif")]

    if not arquivos:
        print("⚠️ Sem dados de insolação → fallback baseado em temperatura")

        temp = np.load(os.path.join(INTERIM_DIR, "temperatura_clean.npy"))
        insol = temp * 1360  # proxy solar

        np.save(os.path.join(INTERIM_DIR, "insolacao_clean.npy"), insol)
        return

    caminho = os.path.join(pasta, arquivos[0])

    print("🌞 Limpando insolação:", caminho)

    arr, meta = carregar_geotiff(caminho)

    # escala solar máxima ~1360 W/m²
    arr = limpar_array(arr, clip_min=0, clip_max=1) * 1360

    np.save(os.path.join(INTERIM_DIR, "insolacao_clean.npy"), arr)
    np.save(os.path.join(INTERIM_DIR, "insolacao_meta.npy"), meta)

    print("✅ insolacao_clean.npy salvo")


# =========================
# 🛰️ LIMPAR IMAGENS LROC
# =========================

def limpar_imagens():

    pasta = os.path.join(RAW_DIR, "lroc")
    out_dir = os.path.join(INTERIM_DIR, "images_clean")

    os.makedirs(out_dir, exist_ok=True)

    arquivos = [f for f in os.listdir(pasta) if f.endswith(".tif")]

    if not arquivos:
        raise Exception("❌ Nenhuma imagem LROC encontrada")

    metadata = []

    print(f"🛰️ Limpando {len(arquivos)} imagens...")

    for i, nome in enumerate(arquivos[:100]):  # limite inicial

        caminho = os.path.join(pasta, nome)

        arr, meta = carregar_geotiff(caminho)

        arr = limpar_array(arr)

        np.save(os.path.join(out_dir, f"img_{i}.npy"), arr)

        metadata.append({
            "index": i,
            "original_file": nome,
            "bounds": meta["bounds"],
            "crs": meta["crs"]
        })

    np.save(os.path.join(INTERIM_DIR, "images_metadata.npy"), metadata)

    print(f"✅ {len(metadata)} imagens limpas")


# =========================
# 🚀 EXECUÇÃO
# =========================

if __name__ == "__main__":

    print("🚀 CLEAN PIPELINE — NASA LRO")

    limpar_temperatura()
    limpar_insolacao()

    try:
        limpar_imagens()
    except Exception as e:
        print("⚠️ Imagens não processadas:", e)

    print("🎯 Dados prontos em INTERIM")