import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_status():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "dimensoes_mapa" in data


def test_analisar_valido():
    response = client.post("/analisar", json={"lat": 10, "lon": 10})
    assert response.status_code == 200
    data = response.json()
    assert "probabilidade_gelo" in data
    assert "temperatura" in data
    assert "insolacao" in data
    assert 0.0 <= data["probabilidade_gelo"] <= 1.0
    # Subsolo: lista de 3 profundidades (0.1m, 0.5m, 1.0m) ou None se mapa ausente
    assert "temperatura_subsolo" in data
    if data["temperatura_subsolo"] is not None:
        assert len(data["temperatura_subsolo"]) == 3
        assert all(isinstance(t, float) for t in data["temperatura_subsolo"])
    # Incerteza Monte Carlo Dropout
    assert "variancia" in data
    assert "confianca" in data
    assert data["variancia"] >= 0.0
    assert data["confianca"] in ("alta", "moderada", "baixa")


def test_analisar_posicao_invalida():
    # Pydantic valida le=179/359 → 422 para valores fora do range
    response = client.post("/analisar", json={"lat": 9999, "lon": 9999})
    assert response.status_code == 422


def test_analisar_tipo_invalido():
    # lat float deve ser rejeitado (modelo espera int)
    response = client.post("/analisar", json={"lat": -89.5, "lon": 45.0})
    assert response.status_code == 422


def test_analisar_negativo_invalido():
    response = client.post("/analisar", json={"lat": -1, "lon": 0})
    assert response.status_code == 422


def test_predict_imagem_grande():
    response = client.post(
        "/predict",
        json={"imagem": [0.5] * 5000, "insolacao": 500.0},
    )
    assert response.status_code == 422


def test_predict_valido():
    imagem = [[0.5] * 32 for _ in range(32)]
    response = client.post(
        "/predict",
        json={"imagem": imagem, "insolacao": 500.0, "temperatura": 200.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "probabilidade_gelo" in data
    assert 0.0 <= data["probabilidade_gelo"] <= 1.0


def test_simular_passos_excede_limite():
    response = client.post("/simular", json={"lat": 5, "lon": 5, "passos": 200})
    assert response.status_code == 422


def test_simular_valido():
    response = client.post("/simular", json={"lat": 5, "lon": 5, "passos": 3})
    assert response.status_code == 200
    data = response.json()
    assert "caminho" in data
    assert len(data["caminho"]) == 3


def test_analisar_com_mapa():
    response = client.post("/analisar_com_mapa", json={"lat": 10, "lon": 10})
    assert response.status_code == 200
    data = response.json()
    assert "mapa" in data
    assert "centro" in data


def test_simular_posicao_invalida():
    response = client.post("/simular", json={"lat": 9999, "lon": 9999, "passos": 3})
    assert response.status_code == 422


def test_analisar_com_mapa_borda():
    # Borda superior-esquerda — raio=2 não deve extrapolar nem lançar exceção
    response = client.post("/analisar_com_mapa", json={"lat": 1, "lon": 1})
    assert response.status_code == 200
    data = response.json()
    assert "mapa" in data
    # Todos os pontos retornados devem estar dentro do mapa
    for ponto in data["mapa"]:
        assert ponto["lat"] >= 0
        assert ponto["lon"] >= 0


def test_predict_imagem_aninhada_grande():
    # Lista aninhada 65x65 = 4225 elementos > 4096 — deve ser rejeitada
    imagem = [[0.5] * 65 for _ in range(65)]
    response = client.post("/predict", json={"imagem": imagem, "insolacao": 500.0})
    assert response.status_code == 422


def test_predict_imagem_aninhada_valida():
    # Lista aninhada 64x64 = 4096 elementos — deve ser aceita
    imagem = [[0.5] * 64 for _ in range(64)]
    response = client.post("/predict", json={"imagem": imagem, "insolacao": 500.0})
    assert response.status_code == 200
    assert 0.0 <= response.json()["probabilidade_gelo"] <= 1.0
