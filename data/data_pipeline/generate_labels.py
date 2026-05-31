"""
Labels independentes para detecção de gelo lunar.

Fonte: PSRs confirmados por instrumentos separados dos inputs do modelo.
Isso evita o problema de circularidade (label = threshold(input)).

Hierarquia de confiança:
  1.0 — LCROSS 2009: impacto + espectroscopia H2O confirmada
  1.0 — Diviner EPF: medicoes de temperatura direta in-situ
  0.9 — LAMP UV: assinatura UV de H2O exposta (PSRs catalogados por literatura)
  0.8 — Mini-RF CPR > 1.0: radar indica gelo subsuperficial
  0.7 — Diviner: cold trap confirmado (T < 54K permanente)

Nota LAMP FITS:
  Os arquivos .fit baixados (parse_lamp.py) contêm séries temporais de contagem UV
  (1D, sem geolocalização por pixel). Para fundi-los espacialmente seria necessário
  calcular o apontamento do instrumento via SCUT_TIME + atitude da espaçonave — pipeline
  não trivial. Os PSRs confirmados por LAMP na literatura já estão em PSR_CONFIRMADOS
  (Shackleton, Peary, Whipple) com confiança 0.9. A função integrar_lamp_labels()
  abaixo é o ponto de entrada para integração futura quando a geolocalização estiver
  disponível.

Refs:
  Colaprete et al. (2010) Science — LCROSS Cabeus
  Gladstone et al. (2010) Science — LAMP Shackleton
  Hayne et al. (2015) JGR — LAMP global hydration map
  Spudis et al. (2010) GRL — Mini-RF PSR north pole
  Paige et al. (2010) Science — Diviner cold traps
  Williams et al. (2019) JGR — Diviner EPF dataset
"""

import os
import numpy as np


def _haversine_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância de arco-grande em graus entre dois pontos lat/lon."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(np.degrees(2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))))

# (lat_deg, lon_deg, raio_deg, confianca, instrumento)
PSR_CONFIRMADOS = [
    # Polo Sul — raios em graus (1 grau ~30 km no polo)
    (-85.32, -35.50, 3.0, 1.0, "LCROSS"),        # Cabeus — gelo confirmado
    (-89.90,   0.00, 2.5, 0.9, "LAMP"),           # Shackleton
    (-87.40,  -4.70, 2.5, 0.8, "Diviner"),        # Haworth
    (-85.20,  53.50, 3.0, 0.75, "Mini-RF"),       # Nobile
    (-84.50,  84.70, 3.5, 0.70, "Diviner"),       # Amundsen
    (-83.00, -52.00, 2.0, 0.65, "Diviner"),       # PSR anonimo sul
    # Polo Norte
    ( 88.60,  33.00, 2.5, 0.85, "LAMP"),          # Peary
    ( 86.10, -89.90, 2.5, 0.90, "Diviner"),       # Hermite
    ( 89.00, 119.90, 2.0, 0.80, "LAMP"),          # Whipple
    ( 85.00,   9.70, 3.0, 0.70, "Mini-RF"),       # Byrd
    ( 84.00, -52.00, 2.0, 0.65, "Diviner"),       # PSR anonimo norte
]

# Locais NEGATIVOS confirmados (sem gelo mesmo sendo frios/escuros)
PSR_NEGATIVOS = [
    (  0.0,   0.0, 5.0),   # equador
    ( 45.0,  90.0, 5.0),   # mid-latitude
    (-45.0, -90.0, 5.0),
]


def gerar_label_map(H: int = 180, W: int = 360) -> tuple:
    """
    Retorna:
      confidence_map: (H, W) float32, 0.0-1.0 por pixel
      binary_map:     (H, W) int32,   0 ou 1
      source_map:     (H, W) string,  instrumento de origem
    """
    confidence = np.zeros((H, W), dtype=np.float32)
    source = np.full((H, W), "", dtype=object)

    # Escala de graus para pixels para qualquer resolucao H x W
    lat_scale = H / 180.0   # pixels por grau de latitude
    lon_scale = W / 360.0   # pixels por grau de longitude

    for (lat_c, lon_c, raio, conf, instrumento) in PSR_CONFIRMADOS:
        i_c = int(round((lat_c + 90) * lat_scale))
        # Pre-filtro em latitude: distância de arco >= |dlat|, então linhas com
        # |lat_i - lat_c| > raio nunca estão dentro do raio de arco-grande.
        raio_i = int(raio * lat_scale) + 2

        for ii in range(max(0, i_c - raio_i), min(H, i_c + raio_i + 1)):
            lat_i = ii / lat_scale - 90.0
            if abs(lat_i - lat_c) > raio:
                continue
            # Próximo ao polo todos os longitudes podem estar dentro do raio —
            # itera todos os j usando haversine para distância correta.
            for jj in range(W):
                lon_j = jj / lon_scale - 180.0
                dist = _haversine_deg(lat_i, lon_j, lat_c, lon_c)
                if dist < raio:
                    score = float(conf * np.exp(-(dist / (raio * 0.5))**2))
                    if score > confidence[ii, jj]:
                        confidence[ii, jj] = score
                        source[ii, jj] = instrumento

    binary = (confidence >= 0.3).astype(np.int32)
    return confidence, binary, source


def integrar_lamp_labels(
    confidence: np.ndarray,
    binary: np.ndarray,
    source: np.ndarray,
    lamp_dir: str = "data/raw/lro/lamp/",
    verbose: bool = True,
) -> tuple:
    """
    Ponto de entrada para integração espacial de dados LAMP FITS.

    Estado atual: as masks geradas por parse_lamp.py são arrays 1D (série temporal
    de housekeeping) sem geolocalização por pixel. Para integração espacial plena
    seria necessário calcular o apontamento da slit do LAMP via SCUT_TIME + atitude
    da espaçonave (não implementado).

    Os PSRs confirmados por LAMP na literatura (Shackleton, Peary, Whipple) já
    constam em PSR_CONFIRMADOS com confianca=0.9, portanto o catálogo já reflete
    o conhecimento LAMP disponível sem as masks 1D.

    Quando a geolocalização estiver disponível, esta função deve:
      1. Ler lat/lon de cada contagem UV via Ancillary Data (SCUT_TIME_SLOW + atitude)
      2. Para pixels com COUNT_RATE < percentil 20 (assinatura de gelo), setar
         confidence[i, j] = max(confidence[i, j], 0.9) e source[i, j] = "LAMP_FITS"
    """
    masks = [f for f in os.listdir(lamp_dir) if f.endswith("_gelo_mask.npy")] if os.path.isdir(lamp_dir) else []
    if not masks:
        return confidence, binary, source

    total_ice = sum(
        int(np.load(os.path.join(lamp_dir, m)).sum()) for m in masks
    )
    if verbose:
        print(f"  LAMP FITS: {len(masks)} mask(s) disponiveis | {total_ice} pixels UV com assinatura de gelo")
        print(f"  LAMP FITS: integracao espacial pendente (geolocation pipeline necessario)")
        print(f"  LAMP FITS: PSRs catalogados por literatura ja incluidos (Shackleton/Peary/Whipple conf=0.9)")

    return confidence, binary, source


def integrar_epf_cabeus(
    confidence: np.ndarray,
    binary: np.ndarray,
    source: np.ndarray,
    csv_path: str = "data/raw/lro/diviner/1917_Cabeus_EPF_alltargeted.csv",
    temp_cold_trap: float = 54.0,
    raio_graus: float = 1.5,
    verbose: bool = True,
) -> tuple:
    """
    Atualiza os mapas de label com medicoes reais Diviner EPF para Cabeus.

    Le o CSV EPF, filtra medicoes de qualidade perto de Cabeus com T < temp_cold_trap,
    e eleva a confianca do pixel correspondente para 1.0 (medicao direta confirmada).

    Ref: Williams et al. (2019) JGR Planets -- Diviner EPF dataset description
         Paige et al. (2010) Science -- cold trap threshold T < 54K
    """
    import csv as _csv

    if not os.path.exists(csv_path):
        if verbose:
            print(f"  EPF CSV nao encontrado: {csv_path}")
        return confidence, binary, source

    H, W = confidence.shape
    lat_scale = H / 180.0
    lon_scale = W / 360.0

    # Cabeus: referencia para filtro espacial
    cabeus_lat, cabeus_lon = -85.32, -35.50

    n_medidas = 0
    n_cold = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            try:
                qual = int(float(row.get("qual", 0)))
                if qual < 0:
                    continue
                tb   = float(row["tb"])
                clat = float(row["clat"])
                clon = float(row["clon"])
            except (ValueError, KeyError):
                continue

            # Filtra por proximidade ao centro de Cabeus
            dist = _haversine_deg(clat, clon, cabeus_lat, cabeus_lon)
            if dist > raio_graus:
                continue

            n_medidas += 1

            if tb < temp_cold_trap:
                n_cold += 1
                # Converte coordenada para indice de grade
                i = int(round((clat + 90) * lat_scale))
                j = int(round((clon + 180) * lon_scale))
                i = max(0, min(H - 1, i))
                j = max(0, min(W - 1, j))

                # Eleva confianca para 1.0 (medicao direta EPF)
                if confidence[i, j] < 1.0:
                    confidence[i, j] = 1.0
                    binary[i, j] = 1
                    source[i, j] = "Diviner_EPF"

    if verbose:
        pct = 100 * n_cold / max(1, n_medidas)
        print(f"  EPF Cabeus: {n_medidas} medicoes proximas | {n_cold} cold trap (T<{temp_cold_trap}K) = {pct:.1f}%")

    return confidence, binary, source


def salvar_labels(
    out_dir: str = "data/processed/lro/",
    epf_csv: str = "data/raw/lro/diviner/1917_Cabeus_EPF_alltargeted.csv",
    verbose: bool = True,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    confidence, binary, source = gerar_label_map()

    # Reporta estado das masks LAMP (integracao espacial pendente)
    confidence, binary, source = integrar_lamp_labels(
        confidence, binary, source, verbose=verbose
    )

    # Integra medicoes reais Diviner EPF (eleva confianca para pixels medidos)
    if verbose:
        print("Integrando Diviner EPF Cabeus...")
    confidence, binary, source = integrar_epf_cabeus(
        confidence, binary, source, csv_path=epf_csv, verbose=verbose
    )

    # Funde com labels Mini-RF CPR se disponivel (preserva deteccoes de radar)
    cpr_path = os.path.join(out_dir, "labels_mini_rf_cpr.npy")
    n_cpr = 0
    if os.path.exists(cpr_path):
        cpr = np.load(cpr_path)
        if cpr.shape == binary.shape:
            cpr_mask = (cpr > 0).astype(np.float32)
            binary = np.maximum(binary.astype(np.float32), cpr_mask)
            # Confianca CPR = 0.8 (Spudis 2010)
            confidence = np.where((cpr_mask > 0) & (confidence < 0.8), 0.8, confidence)
            n_cpr = int(cpr_mask.sum())
            if verbose:
                print(f"  CPR Mini-RF: {n_cpr} pixels de radar fundidos")

    np.save(os.path.join(out_dir, "labels_confianca.npy"), confidence)
    np.save(os.path.join(out_dir, "labels_gelo.npy"), binary.astype(np.float32))
    np.save(os.path.join(out_dir, "labels_fonte.npy"), source)

    stats = {
        "total_pixels":   int(binary.size),
        "positivos":      int(binary.sum()),
        "negativos":      int((binary == 0).sum()),
        "pct_positivo":   float(binary.mean() * 100),
        "conf_media_pos": float(confidence[binary == 1].mean()) if binary.sum() > 0 else 0,
        "psrs_modelados": len(PSR_CONFIRMADOS),
        "epf_integrado":  os.path.exists(epf_csv),
        "cpr_pixels":     n_cpr,
    }

    if verbose:
        print(f"Labels gerados (PSR + EPF + CPR):")
        print(f"  Positivos : {stats['positivos']} pixels ({stats['pct_positivo']:.2f}%)")
        print(f"  Negativos : {stats['negativos']} pixels")
        print(f"  PSRs      : {stats['psrs_modelados']} locais confirmados")
        print(f"  Conf media: {stats['conf_media_pos']:.2f}")
        print(f"  EPF       : {'integrado' if stats['epf_integrado'] else 'nao encontrado'}")
        print(f"  CPR       : {n_cpr} pixels")
        print(f"  Salvo em  : {out_dir}")

    return stats


if __name__ == "__main__":
    salvar_labels()
