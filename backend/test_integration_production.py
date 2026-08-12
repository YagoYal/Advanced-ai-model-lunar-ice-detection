"""
P3 — Testes de integração contra a API em produção (Fly.io).

Diferente de `backend/test_api.py` (que testa a app FastAPI in-process via
`TestClient`, sem rede), este arquivo faz requisições HTTP/WebSocket reais
contra https://lunar-ice-api.fly.dev, validando o que está de fato no ar.

Desligado por padrão (não roda em CI nem em `pytest` normal) — evita:
  - dependência de rede/flakiness em CI
  - acordar o backend do scale-to-zero (cold start ~3-5s) a cada push
  - bater no rate limiter (slowapi) com execuções repetidas em pipeline

Rodar manualmente — endpoints públicos apenas:
    RUN_PROD_INTEGRATION=1 python -m pytest backend/test_integration_production.py -v

Com autenticação (endpoints protegidos por X-API-Key em produção):
    RUN_PROD_INTEGRATION=1 PROD_API_KEY=<key> \
        python -m pytest backend/test_integration_production.py -v

Contra outro ambiente (ex. staging):
    RUN_PROD_INTEGRATION=1 PROD_API_URL=https://outro-host python -m pytest ...
"""
import json
import os

import pytest
import requests

RUN = os.getenv("RUN_PROD_INTEGRATION") == "1"
BASE_URL = os.getenv("PROD_API_URL", "https://lunar-ice-api.fly.dev").rstrip("/")
API_KEY = os.getenv("PROD_API_KEY", "")
AUTH_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

# Cold start do Fly.io (scale-to-zero) pode levar até o grace_period configurado
# (45s no fly.toml) na 1ª requisição depois de idle — timeout generoso de propósito.
COLD_START_TIMEOUT = int(os.getenv("PROD_COLD_START_TIMEOUT", "60"))

pytestmark = pytest.mark.skipif(
    not RUN,
    reason="Integração contra produção desativada por padrão — rode com RUN_PROD_INTEGRATION=1",
)

_needs_key = pytest.mark.skipif(
    not API_KEY,
    reason="PROD_API_KEY não definida — endpoints autenticados pulados",
)


def _get(path, **kwargs):
    return requests.get(f"{BASE_URL}{path}", timeout=COLD_START_TIMEOUT, **kwargs)


def _post(path, json=None, **kwargs):
    return requests.post(f"{BASE_URL}{path}", json=json, timeout=COLD_START_TIMEOUT, **kwargs)


# =========================
# Endpoints públicos (sem auth)
# =========================

def test_health():
    r = _get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_status_root():
    r = _get("/")
    assert r.status_code == 200
    assert "dimensoes_mapa" in r.json()


def test_docs_v1():
    r = _get("/v1/docs")
    assert r.status_code == 200


def test_openapi_v1():
    r = _get("/v1/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_security_headers():
    r = _get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Strict-Transport-Security") is not None, (
        "produção deveria enviar HSTS — checar se ENV=production está setado no Fly.io"
    )


def test_cors_allowed_origin():
    """Confirma que o domínio de produção do Vercel está liberado no CORS real."""
    r = requests.options(
        f"{BASE_URL}/analisar",
        headers={
            "Origin": "https://lunar-ice.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
        timeout=COLD_START_TIMEOUT,
    )
    assert r.headers.get("access-control-allow-origin") in (
        "https://lunar-ice.vercel.app", "*",
    )


# =========================
# Endpoints autenticados (X-API-Key obrigatório em produção)
# =========================

@_needs_key
def test_analisar_rejeita_sem_key():
    r = _post("/analisar", json={"lat": 10, "lon": 10})  # sem header
    assert r.status_code == 403


@_needs_key
def test_analisar_aceita_com_key():
    r = _post("/analisar", json={"lat": 10, "lon": 10}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    for campo in ("probabilidade_gelo", "variancia", "confianca", "temperatura",
                  "temperatura_subsolo", "insolacao", "insolacao_atual",
                  "fase_lunar", "altitude_m"):
        assert campo in data, f"campo ausente em produção: {campo}"
    assert 0.0 <= data["probabilidade_gelo"] <= 1.0


@_needs_key
def test_analisar_psr_sul_shackleton_producao():
    # Shackleton -89.9° → lat_idx=0, lon_idx=180 — PSR confirmado (LAMP/Gladstone 2010)
    r = _post("/analisar", json={"lat": 0, "lon": 180}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["probabilidade_gelo"] >= 0.5, "PSR sul deve ter alta probabilidade em produção"


@_needs_key
def test_analisar_equador_baixa_prob_producao():
    r = _post("/analisar", json={"lat": 90, "lon": 180}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["probabilidade_gelo"] < 0.5


@_needs_key
def test_analisar_posicao_invalida_producao():
    r = _post("/analisar", json={"lat": 9999, "lon": 9999}, headers=AUTH_HEADERS)
    assert r.status_code == 422


@_needs_key
def test_predict_valido_producao():
    imagem = [[0.5] * 64 for _ in range(64)]
    r = _post("/predict", json={"imagem": imagem, "insolacao": 500.0}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert 0.0 <= r.json()["probabilidade_gelo"] <= 1.0


# =========================
# WebSocket /ws/simular — validar que continua sem auth (é intencional, ver main.py)
# =========================

def test_ws_simular_producao():
    import ssl

    import certifi
    from websockets.sync.client import connect

    # websockets usa ssl.create_default_context() puro, que no Windows não cai
    # automaticamente no bundle da certifi (diferente de requests) — sem isso,
    # falha com "certificate has expired" mesmo com o cert do servidor válido
    # (confirmado via curl — é ambiente local, não bug de produção).
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/ws/simular"
    with connect(ws_url, ssl=ssl_ctx, open_timeout=COLD_START_TIMEOUT) as ws:
        ws.send(json.dumps({"lat": 5, "lon": 5, "passos": 3}))
        passos = 0
        while True:
            msg = json.loads(ws.recv(timeout=COLD_START_TIMEOUT))
            if msg.get("done"):
                assert msg["total_passos"] == 3
                break
            assert "probabilidade_gelo" in msg
            passos += 1
        assert passos == 3
