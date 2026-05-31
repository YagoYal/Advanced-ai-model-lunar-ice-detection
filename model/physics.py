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


def temperatura_superficie(insolacao: float, lat=None, tempo=None) -> float:
    """
    Temperatura de equilíbrio radiativo superficial.

    Args:
        insolacao: fluxo solar incidente em W/m² com geometria já aplicada.
                   Usar insolacao_dinamica() ou valor do mapa de insolação como entrada.
    """
    energia = insolacao * (1 - ALBEDO)
    if energia <= 0:
        return 35.0  # PSR ou noite polar
    return float((energia / (SIGMA * EMISSIVIDADE)) ** 0.25)


def perfil_subsolo(temp_superficie: float, insolacao: float = 0.0,
                   profundidade: float = 2.0, camadas: int = 20) -> np.ndarray:
    """
    Temperatura mínima anual por profundidade via difusão periódica (Vasavada 2012).

    T_min(z) = T_mean - A * exp(-z / z_skin)

    T_mean = temperatura média anual superficial.
    A = (π^0.25 - 1) * T_mean — amplitude diurna para regiões iluminadas (slow-rotator,
    Vasavada 2012 §2). O perfil mínimo aumenta com z porque a onda diurna atenua.
    Para PSRs (insolacao ≈ 0): A = 0 → perfil isotérmico em T_mean.

    Args:
        temp_superficie: temperatura média anual superficial em K
        insolacao: insolação média anual em W/m² (0 para PSRs permanentemente sombreados)
        profundidade: profundidade máxima em metros (default 2 m)
        camadas: número de camadas discretas

    Returns:
        np.ndarray shape (camadas,) — temperatura mínima anual por profundidade (K)
    """
    T_mean = max(float(temp_superficie), TEMP_ESPACO)

    # Amplitude diurna: π^0.25 - 1 ≈ 0.331 (Vasavada 2012)
    A = (np.pi ** 0.25 - 1.0) * T_mean if insolacao > 10.0 else 0.0

    profundidades = np.linspace(0, profundidade, camadas)
    T_min = T_mean - A * np.exp(-profundidades / Z_SKIN)
    return np.maximum(T_min, TEMP_ESPACO).astype(np.float32)


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


def features_subsolo(temp_superficie: float, insolacao: float = 0.0,
                     profundidade: float = 2.0, camadas: int = 20) -> np.ndarray:
    """
    Extrai 3 features normalizadas do perfil subsuperficial para uso no modelo.
    Returns: [temp_0.1m_norm, temp_0.5m_norm, temp_1m_norm]  — cada dividido por 300K
    """
    perfil = perfil_subsolo(temp_superficie, insolacao, profundidade, camadas)
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
    temp_sup = temperatura_superficie(insolacao)
    perfil   = perfil_subsolo(temp_sup, insolacao=insolacao)
    gelo     = estabilidade_gelo(perfil)
    return temp_sup, perfil, gelo
