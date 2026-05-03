import os
import numpy as np

# =========================
# 📁 DIRETÓRIOS
# =========================

INTERIM_DIR = "data/interim/lro/cleaned/"
PROCESSED_DIR = "data/processed/lro/"

os.makedirs(PROCESSED_DIR, exist_ok=True)


# =========================
# 🔄 NORMALIZAÇÃO PADRÃO
# =========================

def normalizar(arr):
    arr = arr.astype(np.float32)

    if arr.max() > 0:
        arr = arr / arr.max()

    return arr


# =========================
# 🌡️ PROCESSAR TEMPERATURA
# =========================

def processar_temperatura():

    caminho = os.path.join(INTERIM_DIR, "temperatura_clean.npy")

    if not os.path.exists(caminho):
        raise Exception("❌ temperatura_clean.npy não encontrado (rode clean_nasa_data.py)")

    print("📡 Processando temperatura (interim → processed)")

    temp = np.load(caminho)

    # manter normalizado (já vem limpo)
    temp = normalizar(temp)

    np.save(os.path.join(PROCESSED_DIR, "temperatura.npy"), temp)

    print("✅ temperatura.npy pronto")


# =========================
# 🌞 PROCESSAR INSOLAÇÃO
# =========================

def processar_insolacao():

    caminho = os.path.join(INTERIM_DIR, "insolacao_clean.npy")

    if not os.path.exists(caminho):
        raise Exception("❌ insolacao_clean.npy não encontrado")

    print("🌞 Processando insolação")

    insol = np.load(caminho)

    # garantir escala consistente
    insol = normalizar(insol)

    np.save(os.path.join(PROCESSED_DIR, "insolacao.npy"), insol)

    print("✅ insolacao.npy pronto")


# =========================
# 🛰️ PROCESSAR IMAGENS
# =========================

def processar_imagens():

    pasta = os.path.join(INTERIM_DIR, "images_clean")
    out_dir = os.path.join(PROCESSED_DIR, "imagens")

    os.makedirs(out_dir, exist_ok=True)

    arquivos = sorted([f for f in os.listdir(pasta) if f.endswith(".npy")])

    if not arquivos:
        raise Exception("❌ Nenhuma imagem limpa encontrada")

    print(f"🛰️ Processando {len(arquivos)} imagens...")

    metadata_in_path = os.path.join(INTERIM_DIR, "images_metadata.npy")
    metadata_in = np.load(metadata_in_path, allow_pickle=True) if os.path.exists(metadata_in_path) else None

    metadata_out = []

    for i, nome in enumerate(arquivos):

        caminho = os.path.join(pasta, nome)
        img = np.load(caminho).astype(np.float32)

        # normalização final
        img = normalizar(img)

        # salvar imagem processada
        np.save(os.path.join(out_dir, f"img_{i}.npy"), img)

        # 🔥 enriquecer metadata
        meta = {
            "index": i,
            "file": nome
        }

        if metadata_in is not None:
            meta.update(metadata_in[i])

        metadata_out.append(meta)

    np.save(os.path.join(PROCESSED_DIR, "metadata.npy"), metadata_out)

    print("✅ imagens + metadata prontos")


# =========================
# 🧠 ALINHAMENTO ESPACIAL (OPCIONAL FUTURO)
# =========================

def verificar_alinhamento(temp, insol):
    """
    Garante que temperatura e insolação têm mesma resolução
    """
    if temp.shape != insol.shape:
        raise Exception("❌ temperatura e insolação com shapes diferentes")


# =========================
# 🚀 EXECUÇÃO
# =========================

if __name__ == "__main__":

    print("🚀 PROCESS PIPELINE — INTERIM → PROCESSED")

    processar_temperatura()
    processar_insolacao()

    # validar consistência
    temp = np.load(os.path.join(PROCESSED_DIR, "temperatura.npy"))
    insol = np.load(os.path.join(PROCESSED_DIR, "insolacao.npy"))

    verificar_alinhamento(temp, insol)

    try:
        processar_imagens()
    except Exception as e:
        print("⚠️ Imagens não processadas:", e)

    print("🎯 Dataset pronto para IA")