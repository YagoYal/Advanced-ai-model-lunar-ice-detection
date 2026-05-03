import numpy as np

SIGMA          = 5.670374419e-8   # W/m²K⁴
ALBEDO         = 0.12             # regolito lunar (Hapke 2012)
EMISSIVIDADE   = 0.95
TEMP_ESPACO    = 3.0              # K
TEMP_CRITICO_GELO = 110.0        # K — limite de estabilidade do gelo (Paige 2010)

# Propriedades térmicas do regolito lunar (Vasavada 2012)
DIFUSIVIDADE_TERMICA = 4.7e-7    # m²/s  (superfície solta)
PERIODO_LUNAR        = 2.551e6   # s     (~29.5 dias)
# Comprimento de penetração térmica: z_skin = sqrt(κ·P/π)
Z_SKIN = np.sqrt(DIFUSIVIDADE_TERMICA * PERIODO_LUNAR / np.pi)  # ~0.62 m


def angulo_solar(lat, tempo):
    lat_rad = np.radians(lat)
    fase = 2 * np.pi * tempo
    ang = np.cos(lat_rad) * np.cos(fase)
    return max(ang, 0)


def insolacao_dinamica(lat: float, tempo: float) -> float:
    """
    Insolação instantânea em W/m² em função da latitude e fase do ciclo lunar.

    Args:
        lat: latitude em graus (-90 a +90)
        tempo: fase do ciclo lunar (0.0 a 1.0, onde 1.0 = 29.5 dias)

    Returns:
        Insolação em W/m² (0 a ~1361)
    """
    SOLAR_CONSTANT = 1361.0   # W/m²
    fator = angulo_solar(lat, tempo)
    return float(SOLAR_CONSTANT * fator)


def temperatura_superficie(insolacao, lat, tempo):
    fator = angulo_solar(lat, tempo)
    energia = insolacao * (1 - ALBEDO) * fator
    if energia <= 0:
        return 35.0  # PSR
    return float((energia / (SIGMA * EMISSIVIDADE)) ** 0.25)


def perfil_subsolo(temp_superficie, profundidade=2.0, camadas=20):
    """
    Perfil de temperatura subsuperficial via solução analítica da equação de difusão
    para regime periódico (média anual lunar).

    Solução: T(z) = T_mean + (T_sup - T_mean) * exp(-z / z_skin)
    Ref: Vasavada et al. 2012, JGR Planets.

    Args:
        temp_superficie: temperatura média anual da superfície (K)
        profundidade: profundidade máxima em metros (default 2 m)
        camadas: número de camadas discretas

    Returns:
        np.ndarray shape (camadas,) — temperatura por profundidade (K)
    """
    # Temperatura de equilíbrio radiativo profundo (fluxo geotérmico lunar ~18 mW/m²)
    # Para profundidades < 2m, dominada pela difusão solar, não geotérmica
    T_mean = max(temp_superficie * 0.8, TEMP_ESPACO)  # média ponderada conservadora

    profundidades = np.linspace(0, profundidade, camadas)

    # Solução analítica da difusão periódica: atenuação exponencial com z_skin
    perfil = T_mean + (temp_superficie - T_mean) * np.exp(-profundidades / Z_SKIN)

    return perfil.astype(np.float32)


def estabilidade_gelo(perfil_temp):
    """
    Retorna True se alguma camada subsuperficial for fria o suficiente para
    preservar gelo de água (<110K), e reporta a profundidade mínima estável.
    """
    estavel = perfil_temp < TEMP_CRITICO_GELO
    return bool(np.any(estavel))


def profundidade_estavel_gelo(perfil_temp, profundidade_max=2.0):
    """
    Retorna a profundidade (m) a partir da qual o gelo é estável, ou None.
    """
    camadas = len(perfil_temp)
    profundidades = np.linspace(0, profundidade_max, camadas)
    for z, t in zip(profundidades, perfil_temp):
        if t < TEMP_CRITICO_GELO:
            return float(z)
    return None


def features_subsolo(temp_superficie, profundidade=2.0, camadas=20):
    """
    Extrai 3 features normalizadas do perfil subsuperficial para uso no modelo.
    Returns: [temp_0.1m_norm, temp_0.5m_norm, temp_1m_norm]  — cada dividido por 300K
    """
    perfil = perfil_subsolo(temp_superficie, profundidade, camadas)
    profundidades = np.linspace(0, profundidade, camadas)

    def _interp(z_alvo):
        idx = np.searchsorted(profundidades, z_alvo)
        idx = np.clip(idx, 0, camadas - 1)
        return perfil[idx]

    return np.array([
        _interp(0.1) / 300.0,
        _interp(0.5) / 300.0,
        _interp(1.0) / 300.0,
    ], dtype=np.float32)


def simular_cratera(lat, tempo, insolacao, sombra=False):
    if sombra:
        insolacao *= 0.03  # PSR realista
    temp_sup = temperatura_superficie(insolacao, lat, tempo)
    perfil   = perfil_subsolo(temp_sup)
    gelo     = estabilidade_gelo(perfil)
    return temp_sup, perfil, gelo
