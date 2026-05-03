import logging
import os

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from autonomy.environment import AmbienteLunar
from autonomy.planner import Planner
from autonomy.rover import Rover
from model.hybrid_model import modelo_hibrido, prever_com_incerteza, tempo_lunar
from model.physics import insolacao_dinamica

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =========================
# APP + RATE LIMITER
# =========================

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Lunar Ice Intelligence API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =========================
# HTTPS + SECURITY HEADERS
# =========================

ENV = os.getenv("ENV", "development")

# =========================
# API KEY AUTH
# =========================

API_KEY = os.getenv("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verificar_api_key(key: str = Security(_api_key_header)):
    if ENV != "production":
        return  # auth desativada em desenvolvimento
    if not API_KEY:
        return  # sem key configurada = sem auth (aviso no startup)
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="API key inválida ou ausente.")

if ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# =========================
# CORS
# =========================

_origins_env = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = _origins_env.split(",") if _origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# =========================
# DATA
# =========================

MODE = os.getenv("DATA_MODE", "real")
DATA_DIR = "data/processed/lro/mock/" if MODE == "mock" else "data/processed/lro/"

logger.info("Backend iniciado em modo %s usando %s", MODE.upper(), DATA_DIR)


def carregar_mapas():
    """Carrega grades como arrays numpy — O(1) de memória vs O(H*W) de dicts."""
    try:
        temp_path   = os.path.join(DATA_DIR, "temperatura.npy")
        insol_path  = os.path.join(DATA_DIR, "insolacao.npy")

        if not os.path.exists(temp_path):
            raise FileNotFoundError("temperatura.npy não existe")
        temp = np.load(temp_path)
        if temp.size == 0:
            raise ValueError("temperatura.npy vazio")

        if not os.path.exists(insol_path):
            raise FileNotFoundError("insolacao.npy não existe")
        insol = np.load(insol_path)
        if insol.size == 0:
            raise ValueError("insolacao.npy vazio")

    except Exception as e:
        logger.warning("Usando mapas simulados: %s", e)
        temp  = np.random.rand(64, 64).astype(np.float32)
        insol = (np.random.rand(64, 64) * 1000).astype(np.float32)

    # Mapa subsuperficial (H, W, 20) — opcional, fallback None
    subsolo_path = os.path.join(DATA_DIR, "temperatura_subsolo.npy")
    if os.path.exists(subsolo_path):
        subsolo = np.load(subsolo_path)
        logger.info("Mapa subsolo carregado: %s", str(subsolo.shape))
    else:
        subsolo = None
        logger.warning("temperatura_subsolo.npy ausente — subsolo indisponivel na API")

    h, w = temp.shape
    img_dir = os.path.join(DATA_DIR, "imagens")
    n_imgs = len([f for f in os.listdir(img_dir) if f.endswith(".npy")]) if os.path.isdir(img_dir) else 0

    return temp, insol, subsolo, img_dir, n_imgs, h, w


arr_temperatura, arr_insolacao, arr_subsolo, IMG_DIR, N_IMGS, H, W = carregar_mapas()

ambiente = AmbienteLunar(
    arr_insolacao=arr_insolacao,
    arr_temperatura=arr_temperatura,
    arr_temp_subsolo=arr_subsolo,
    img_dir=IMG_DIR,
    n_imgs=N_IMGS,
)

# =========================
# UTIL
# =========================


def validar_posicao(lat: int, lon: int) -> None:
    if not (0 <= lat < H and 0 <= lon < W):
        raise HTTPException(
            status_code=400,
            detail=f"Posição inválida: ({lat}, {lon}) fora do mapa ({H}x{W})",
        )


# =========================
# MODELS
# =========================


class RequestAnalise(BaseModel):
    lat: int = Field(..., ge=0, le=179)
    lon: int = Field(..., ge=0, le=359)


class RequestSimulacao(BaseModel):
    lat: int = Field(..., ge=0, le=179)
    lon: int = Field(..., ge=0, le=359)
    passos: int = Field(default=10, ge=1, le=100)


class InputPredict(BaseModel):
    imagem: list
    insolacao: float
    temperatura: float | None = None
    latitude: float = 0.0

    @field_validator("imagem")
    @classmethod
    def validar_tamanho_imagem(cls, v):
        # Conta elementos totais para suportar lista plana e lista aninhada
        total = sum(len(row) if isinstance(row, list) else 1 for row in v)
        if total > 4096:
            raise ValueError(f"imagem excede limite de 4096 elementos ({total} recebidos)")
        return v


# =========================
# HEALTH
# =========================


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def status():
    return {"status": "ativo", "dimensoes_mapa": [H, W]}


# =========================
# ANALISE
# =========================


@app.post("/analisar")
@limiter.limit("30/minute")
def analisar(req: RequestAnalise, request: Request, _: None = Depends(verificar_api_key)):
    validar_posicao(req.lat, req.lon)
    try:
        imagem, insolacao, temperatura = ambiente.get_dados_completo((req.lat, req.lon))
        prob, variancia = prever_com_incerteza(
            imagem=imagem, insolacao=insolacao, temperatura=temperatura, lat=req.lat - 90
        )

        # Confiança derivada da variância: baixa var = alta confiança
        if variancia < 0.005:
            confianca = "alta"
        elif variancia < 0.02:
            confianca = "moderada"
        else:
            confianca = "baixa"

        # Perfil subsuperficial — 3 profundidades-chave (0.1m, 0.5m, 1.0m) em K
        if arr_subsolo is not None:
            s = arr_subsolo[req.lat, req.lon]   # (20,)
            temp_subsolo = [round(float(s[1]), 2), round(float(s[5]), 2), round(float(s[10]), 2)]
        else:
            temp_subsolo = None

        lat_graus = float(req.lat - 90)
        t_lunar   = tempo_lunar()
        insol_atual = insolacao_dinamica(lat_graus, t_lunar)

        return {
            "lat": req.lat,
            "lon": req.lon,
            "probabilidade_gelo": float(prob),
            "variancia": round(float(variancia), 6),
            "confianca": confianca,
            "temperatura": float(temperatura),
            "temperatura_subsolo": temp_subsolo,
            "insolacao": float(insolacao),
            "insolacao_atual": round(insol_atual, 2),   # instantânea no ciclo lunar atual
            "fase_lunar": round(t_lunar, 4),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro em /analisar lat=%d lon=%d", req.lat, req.lon)
        raise HTTPException(status_code=500, detail="Erro interno ao processar análise")


# =========================
# MAPA LOCAL
# =========================


@app.post("/analisar_com_mapa")
@limiter.limit("10/minute")
def analisar_com_mapa(req: RequestAnalise, request: Request, _: None = Depends(verificar_api_key)):
    validar_posicao(req.lat, req.lon)
    raio = 2
    resultados = []

    for i in range(req.lat - raio, req.lat + raio + 1):
        for j in range(req.lon - raio, req.lon + raio + 1):
            if 0 <= i < H and 0 <= j < W:
                try:
                    img, ins, temp = ambiente.get_dados_completo((i, j))
                    prob = modelo_hibrido(
                        imagem=img, insolacao=ins, temperatura=temp, lat=i - 90
                    )
                    resultados.append({"lat": i, "lon": j, "prob": float(prob)})
                except Exception as e:
                    logger.warning("Ponto (%d,%d) falhou: %s", i, j, e)
                    continue

    return {"centro": [req.lat, req.lon], "mapa": resultados}


# =========================
# SIMULACAO ROVER
# =========================


@app.post("/simular")
@limiter.limit("20/minute")
def simular(req: RequestSimulacao, request: Request, _: None = Depends(verificar_api_key)):
    validar_posicao(req.lat, req.lon)
    rover = Rover([req.lat, req.lon])
    planner = Planner(rover, ambiente)
    caminho = []

    for _ in range(req.passos):
        mov = planner.passo()
        pos = rover.get_pos()
        try:
            img, ins, temp = ambiente.get_dados_completo(tuple(pos))
            prob = modelo_hibrido(imagem=img, insolacao=ins, temperatura=temp, lat=pos[0] - 90)
        except Exception as e:
            logger.warning("Rover em %s falhou: %s", pos, e)
            prob = None

        caminho.append({"movimento": mov, "posicao": pos, "probabilidade_gelo": prob})

    return {"inicio": [req.lat, req.lon], "caminho": caminho}


# =========================
# PREDICT DIRETO
# =========================


@app.post("/predict")
@limiter.limit("20/minute")
def predict(data: InputPredict, request: Request, _: None = Depends(verificar_api_key)):
    try:
        imagem = np.array(data.imagem, dtype=np.float32)
        prob = modelo_hibrido(
            imagem=imagem,
            insolacao=data.insolacao,
            temperatura=data.temperatura,
            lat=data.latitude,
        )
        return {"probabilidade_gelo": float(prob)}
    except Exception:
        logger.exception("Erro em /predict")
        raise HTTPException(status_code=500, detail="Erro interno ao processar predição")
