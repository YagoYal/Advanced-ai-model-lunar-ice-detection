import json
import logging
import os
import time

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request, Security, WebSocket, WebSocketDisconnect
from fastapi.security.api_key import APIKeyHeader
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
from model.interpret import physics_attribution
from model.physics import insolacao_dinamica

class _JsonFormatter(logging.Formatter):
    """Emite cada linha de log como JSON — compatível com Railway/Vercel log drains."""
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts":     self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key in ("lat", "lon", "duration_ms", "endpoint"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def _setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper()))


_setup_logging()
logger = logging.getLogger(__name__)

# =========================
# APP + RATE LIMITER
# =========================

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Lunar Ice Intelligence API",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)
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
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")

if ENV == "production":
    if not API_KEY:
        logger.warning("API_KEY não definida em produção — todos os requests serão aceitos sem autenticação.")

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
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] if _origins_env else ["*"]

if ENV == "production" and ALLOWED_ORIGINS == ["*"]:
    logger.warning("ALLOWED_ORIGINS não definida em produção — CORS aceita qualquer origem.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
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
        temp  = np.random.rand(180, 360).astype(np.float32)
        insol = (np.random.rand(180, 360) * 1000).astype(np.float32)

    # Mapa subsuperficial (H, W, 20) — opcional, fallback None
    subsolo_path = os.path.join(DATA_DIR, "temperatura_subsolo.npy")
    if os.path.exists(subsolo_path):
        subsolo = np.load(subsolo_path)
        logger.info("Mapa subsolo carregado: %s", str(subsolo.shape))
    else:
        subsolo = None
        logger.warning("temperatura_subsolo.npy ausente — subsolo indisponivel na API")

    # Mapa de altitude LOLA (H, W) float32, metros — opcional, fallback None
    altitude_path = os.path.join(DATA_DIR, "altitude.npy")
    if os.path.exists(altitude_path):
        altitude = np.load(altitude_path)
        logger.info("Mapa altitude LOLA carregado: %s", str(altitude.shape))
    else:
        altitude = None
        logger.warning("altitude.npy ausente — altitude_m indisponivel na API")

    h, w = temp.shape
    img_dir = os.path.join(DATA_DIR, "imagens")
    n_imgs = len([f for f in os.listdir(img_dir) if f.endswith(".npy")]) if os.path.isdir(img_dir) else 0

    return temp, insol, subsolo, altitude, img_dir, n_imgs, h, w


arr_temperatura, arr_insolacao, arr_subsolo, arr_altitude, IMG_DIR, N_IMGS, H, W = carregar_mapas()

ambiente = AmbienteLunar(
    arr_insolacao=arr_insolacao,
    arr_temperatura=arr_temperatura,
    arr_temp_subsolo=arr_subsolo,
    arr_altitude=arr_altitude,
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
            detail=f"Invalid position: ({lat}, {lon}) out of map bounds ({H}x{W})",
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
    t0 = time.perf_counter()
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

        altitude_m_raw = ambiente.get_altitude((req.lat, req.lon))
        altitude_m = round(altitude_m_raw, 1) if altitude_m_raw is not None else None

        try:
            attr = physics_attribution(lat=lat_graus, insolacao=insolacao, temperatura=temperatura)
        except Exception:
            attr = None

        logger.info("analisar", extra={
            "endpoint": "/analisar",
            "lat": req.lat, "lon": req.lon,
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
        })

        return {
            "lat": req.lat,
            "lon": req.lon,
            "probabilidade_gelo": float(prob),
            "variancia": round(float(variancia), 6),
            "confianca": confianca,
            "temperatura": float(temperatura),
            "temperatura_subsolo": temp_subsolo,
            "insolacao": float(insolacao),
            "insolacao_atual": round(insol_atual, 2),
            "fase_lunar": round(t_lunar, 4),
            "altitude_m": altitude_m,
            "physics_attribution": attr,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro em /analisar", extra={"lat": req.lat, "lon": req.lon})
        raise HTTPException(status_code=500, detail="Internal error processing analysis")


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
# SIMULACAO ROVER — WebSocket (streaming)
# =========================


@app.websocket("/ws/simular")
async def ws_simular(ws: WebSocket):
    await ws.accept()
    try:
        payload = await ws.receive_json()
        lat    = int(payload.get("lat", 0))
        lon    = int(payload.get("lon", 0))
        passos = max(1, min(int(payload.get("passos", 10)), 100))

        if not (0 <= lat < H and 0 <= lon < W):
            await ws.send_json({"erro": f"Posição inválida: ({lat}, {lon})"})
            await ws.close(code=1008)
            return

        rover   = Rover([lat, lon])
        planner = Planner(rover, ambiente)

        for passo in range(passos):
            mov = planner.passo()
            pos = rover.get_pos()
            try:
                img, ins, temp = ambiente.get_dados_completo(tuple(pos))
                prob = modelo_hibrido(imagem=img, insolacao=ins, temperatura=temp, lat=pos[0] - 90)
            except Exception:
                prob = None

            await ws.send_json({
                "passo": passo + 1,
                "movimento": mov,
                "posicao": pos,
                "probabilidade_gelo": float(prob) if prob is not None else None,
            })

        await ws.send_json({"done": True, "total_passos": passos})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("Erro em /ws/simular")
        try:
            await ws.send_json({"erro": str(e)})
        except Exception:
            pass


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
        raise HTTPException(status_code=500, detail="Internal error processing prediction")
