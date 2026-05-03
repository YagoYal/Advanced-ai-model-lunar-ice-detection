# Caminhos
DATA_PATH       = "data/"
RAW_PATH        = DATA_PATH + "raw/lro/"
INTERIM_PATH    = DATA_PATH + "interim/lro/cleaned/"
PROCESSED_PATH  = DATA_PATH + "processed/lro/"
MOCK_PATH       = PROCESSED_PATH + "mock/"

# URLs PDS NASA
LROC_URL        = "https://pds-imaging.jpl.nasa.gov/data/lro/"
DIVINER_EPF_URL = (
    "https://pds-geosciences.wustl.edu/lro/"
    "urn-nasa-pds-lro_diviner_derived2/data_derived_epf/"
)
LOLA_URL        = (
    "https://pds-geosciences.wustl.edu/lro/"
    "lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/"
)

# Grade do mapa (1° por pixel)
GRID_LAT   = 180   # -90° a +89°
GRID_LON   = 360   # -180° a +179°

# Constantes físicas (Paige et al. 2010)
TEMP_ICE_STABLE_K  = 110.0    # K — limiar de estabilidade do gelo de H2O
SOLAR_CONSTANT_WM2 = 1361.0   # W/m²
