# Lunar Ice Intelligence

Plataforma de detecção de gelo lunar por IA com dados reais do LRO (Lunar Reconnaissance Orbiter), navegação autônoma de rover via DQN e interface web interativa.

**Demo ao vivo:** [advanced-ai-model-lunar-ice-detecti.vercel.app](https://lunar-ice.vercel.app)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20014594.svg)](https://doi.org/10.5281/zenodo.20014594)

---

## O que o sistema faz

- Baixa e processa dados reais de temperatura (Diviner), radar (Mini-RF CPR), imagens (LROC WAC) e UV (LAMP) da NASA via streaming seletivo — sem baixar arquivos de GBs inteiros
- Treina uma CNN multimodal com labels baseadas em PSRs confirmados por instrumentos independentes (LCROSS, LAMP, Mini-RF, Diviner EPF) — sem circularidade
- Serve uma API FastAPI onde o usuário clica num ponto do mapa lunar e recebe probabilidade de gelo
- Um agente DQN navega o grid lunar autonomamente buscando regiões com maior probabilidade de gelo
- A trajetória do rover é desenhada em tempo real no mapa

---

## Início rápido

```bash
# Primeira vez — instala deps, gera dados, treina e sobe os servidores
./start.sh --full

# Do segundo uso em diante
./start.sh --skip-tests
```

Ou via Makefile:

```bash
make install    # deps Python + Node
make pipeline   # dados + labels + treino
make dev        # sobe servidores
```

---

## Estrutura do projeto

```text
lunar-ice-intelligence/
├── backend/
│   ├── main.py               FastAPI + rate limiting + API key auth + security headers; AmbienteLunar via arrays numpy
│   └── test_api.py           15 testes de integração (pytest + TestClient)
├── model/
│   ├── cnn.py                LunarCNN: CNNEncoder(64×64) + PhysicsEncoder(input_dim=5) + FusionHead
│   ├── physics.py            Stefan-Boltzmann, perfil_subsolo T(z), insolacao_dinamica, features_subsolo
│   ├── hybrid_model.py       Inferência e treino incremental
│   ├── train.py              WeightedBCELoss, Adam, CosineAnnealing, TRAIN_EPOCHS (default 30)
│   ├── validate.py           Validação em 6 PSRs com patches reais do dataset
│   └── benchmark.py          Benchmark contra 14 locais catalogados (4 publicações)
├── autonomy/
│   ├── rover.py              Rover com energia e histórico; longitude circular
│   ├── environment.py        AmbienteLunar: acesso O(1) via arrays numpy; arr_temp_subsolo opcional
│   ├── planner.py            Planner greedy (strategy.py); clip bounds via shape real
│   ├── strategy.py           simular_movimento() com clip H/W reais
│   ├── rl_env.py             MDP lunar; obs_dim=6; bonus_subsolo max(0,1−temp_sub_n)×0.4
│   ├── rl_agent.py           Double DQN, obs_dim=6, replay buffer 10k, soft update τ=0.005
│   ├── train_rl.py           Loop de treino RL (500 episódios)
│   └── simulation.py         Simulação local sem dicts O(H×W)
├── data/
│   ├── data_pipeline/
│   │   ├── generate_scientific_data.py   Grade 180×360 (temp + insol + temp_subsolo + patches); labels delegados
│   │   ├── generate_labels.py            Labels PSR + EPF Diviner + Mini-RF CPR fundidos
│   │   ├── filter_nasa_data.py           Streaming vsicurl; insolacao.npy sempre (180,360)
│   │   ├── clean_nasa_data.py            Limpeza e validação dos arrays NASA
│   │   ├── process_nasa_data.py          Processamento intermediário
│   │   ├── dataset.py                    LunarDataset PyTorch; features(5,): [insol_norm,lat_norm,sub_0.1m,sub_0.5m,sub_1.0m]
│   │   ├── coords.py                     Fonte única grade↔graus: lat=i−90, lon=j−180
│   │   ├── config.py                     Constantes e caminhos centralizados
│   │   └── download.py                   Entry point: --diviner-epf --lamp --lroc-polar --tudo
│   ├── raw/lro/
│   │   ├── diviner/download_diviner.py   EPF de PSRs (~15 MB); Cabeus 549k medições cold trap
│   │   ├── lroc/download_lroc_polar.py   Patches polares Haworth/Nobile/Peary (PDS→COG→sintético)
│   │   ├── mini_rf/                      CPR polar via HTTP range requests (59 MB)
│   │   └── lamp/parse_lamp.py            LAMP FITS parser; COUNT_RATE; 2 arquivos ~10 MB
│   └── processed/lro/
│       ├── temperatura.npy               180×360, Kelvin
│       ├── insolacao.npy                 180×360, W/m²
│       ├── temperatura_subsolo.npy       180×360×20, Kelvin (20 camadas até 2 m)
│       ├── labels_gelo.npy               PSR + EPF + CPR fundidos — 14 656 positivos (22.6%)
│       ├── labels_confianca.npy          Confiança por fonte (EPF=1.0, CPR=0.8, PSR catálogo)
│       ├── labels_mini_rf_cpr.npy        CPR > 1.0 por pixel
│       └── imagens/                      50 patches 64×64 (inclui Haworth/Nobile/Peary calibrados)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                       Landing page com 8 seções
│   │   ├── sections/
│   │   │   ├── HeroSection.jsx
│   │   │   ├── SobreSection.jsx
│   │   │   ├── ArquiteturaSection.jsx
│   │   │   ├── CienciaSection.jsx
│   │   │   ├── DadosSection.jsx
│   │   │   ├── AnaliseSection.jsx
│   │   │   ├── RoverSection.jsx
│   │   │   └── ReferenciasSection.jsx
│   │   ├── services/api.js               analisar / simular / analisarComMapa
│   │   ├── services/api.test.js          8 testes (vitest)
│   │   └── components/
│   │       ├── RoverPath.jsx             Trajetória rover (conversão grade→graus correta)
│   │       ├── RoverPath.test.jsx        6 testes de renderização e lógica
│   │       ├── LunarMap.jsx              MapContainer reutilizável
│   │       └── Heatmap.jsx               Heatmap de probabilidade
│   └── index.html
├── Dockerfile                            python:3.13-slim, non-root, apt-get upgrade
├── docker-compose.yml                    volumes data/ e model/, healthcheck, restart
├── Makefile
├── pytest.ini                            testpaths: backend model autonomy
├── requirements.txt
└── start.sh                              --train --train-rl --validate --full --skip-tests --only-tests
```

---

## Dados reais integrados

| Instrumento | Dado | Como baixado | Tamanho |
|---|---|---|---|
| Diviner LRO | Temperatura polar | vsicurl GeoTIFF, faixas \|lat\|≥60° | ~472 MB stream → 260 KB salvo |
| Diviner EPF | Temperaturas PSR medidas diretamente | PDS download direto | ~15 MB |
| LROC WAC | Patches imagem 64×64 | vsicurl USGS COG por PSR; sintético calibrado (Sato 2014) para polos | ~1 MB |
| Mini-RF | CPR polar (radar gelo) | HTTP range requests, faixas polares | 59 MB |
| LAMP | Assinatura UV de H₂O (FITS) | PDS download direto | ~10 MB |

```bash
make download-all          # Diviner EPF + LAMP + LROC polares (~85 MB)
make download-lola         # Diviner GeoTIFF polar via vsicurl
make download-lroc-polar   # Patches Haworth / Nobile / Peary
```

---

## Modelo de IA

**Arquitetura:** LunarCNN multimodal

```
Entrada imagem 64×64  → CNNEncoder (3× Conv+BN+ReLU+MaxPool) → 128 features
Entrada física [insol_norm, lat_norm, sub_0.1m, sub_0.5m, sub_1.0m]  → PhysicsEncoder (MLP 5→32→64→64) → 64 features
Concatenação 192D  → FusionHead (Linear 192→128→64→1) → sigmoid → P(gelo)
```

**Labels — sem circularidade:**

| Fonte | Confiança | Positivos | Referência |
|---|---|---|---|
| LCROSS impacto Cabeus | 1.0 | 1 | Colaprete et al. (2010) Science |
| Diviner EPF medições diretas | 1.0 | ~6 | Williams et al. (2019) JGR |
| LAMP UV Shackleton | 0.9 | 2 | Gladstone et al. (2010) Science |
| Mini-RF CPR > 1.0 | 0.8 | 14 655 | Spudis et al. (2010) GRL |
| Diviner cold trap | 0.7 | ~50 | Paige et al. (2010) Science |
| **Total** | | **14 656** | |

**Física subsuperficial (Vasavada 2012):**

```
T(z) = T_mean + (T_sup − T_mean) × exp(−z / z_skin)
z_skin = 0.62 m   (√(κ·P/π), κ=4.7×10⁻⁷ m²/s, P=2.551×10⁶ s)
Profundidades monitoradas: 0.1 m, 0.5 m, 1.0 m → features_subsolo
```

**Resultados do treino (30 epochs, CPU):**

```
Dataset  : 58 624 exemplos  |  14 656 positivos (25%)
val_loss : 0.0109
F1       : 0.997
Recall   : 1.000
Acc      : 0.998
```

**Benchmark (14 locais, 4 publicações):**

```
Cabeus      (LCROSS 2009)    prob=0.983   GELO    OK
Shackleton  (LAMP UV)        prob=1.000   GELO    OK
Haworth     (Mini-RF CPR)    prob=1.000   GELO    OK
Nobile      (Diviner cold)   prob=0.000   GELO    !!  — baixa confiança (0.75)
Amundsen    (PSR catalog)    prob=0.000   GELO    !!  — baixa confiança (0.70)
Hermite     (Paige 26K)      prob=1.000   GELO    OK
Peary       (CPR norte)      prob=1.000   GELO    OK
Whipple     (PSR norte)      prob=1.000   GELO    OK
Equador     (controle)       prob=0.000   SEM     OK
Mare Tranq  (Apollo 11)      prob=0.000   SEM     OK
Copernicus  (crater jovem)   prob=0.000   SEM     OK
Tycho       (mid-lat)        prob=0.000   SEM     OK
Mid-lat 40N (iluminado)      prob=0.000   SEM     OK
Mid-lat 40S (iluminado)      prob=0.000   SEM     OK
Total: 12/14 corretos (86%) | PSRs: 6/8 | Negativos: 6/6
```

---

## Rover autônomo (DQN)

- **Estado (obs_dim=6):** `[lat_norm, lon_norm, energia_norm, insol_norm, prob_gelo, temp_sub_norm]`
- **Ações:** N, S, E, W
- **Reward:** `ganho_ice_prob − custo_energia + bonus_descoberta + bonus_subsolo`
  - `bonus_subsolo = max(0, 1 − temp_sub_norm) × 0.4`
- **Rede:** Double DQN, replay buffer 10k, target network soft update τ=0.005, epsilon-greedy com decay 5k steps

```bash
make train-rl    # treina 500 episódios → model/rl_pesos.pth
make demo-rl     # roda agente treinado e exibe trajetória
```

---

## API

| Endpoint | Método | Rate limit | Descrição |
|---|---|---|---|
| `/analisar` | POST | 30/min | Probabilidade de gelo em (lat, lon) |
| `/analisar_com_mapa` | POST | 10/min | Grade 5×5 ao redor do ponto |
| `/simular` | POST | 20/min | Simulação rover (1–100 passos) |
| `/predict` | POST | 20/min | Inferência direta com imagem |
| `/health` | GET | — | Health check |

**Sistema de coordenadas:** `lat` e `lon` são índices de grade inteiros (0–179, 0–359). `lat_graus = lat − 90`, `lon_graus = lon − 180`.

**Resposta `/analisar` (8 campos):** `probabilidade_gelo`, `variancia`, `confianca`, `temperatura`, `temperatura_subsolo[3]`, `insolacao`, `insolacao_atual`, `fase_lunar`.

**Autenticação:** header `X-API-Key` (opcional em dev). Segurança: CSP, X-Frame-Options, HSTS em produção.

---

## Testes

```bash
make test           # 15 testes backend (pytest)
make test-frontend  # 13 testes frontend (vitest — api + RoverPath)
make test-all       # ambos
```

---

## Deploy

**Produção (Railway + Vercel):**

| Serviço | Plataforma | URL |
|---|---|---|
| Backend (FastAPI) | Railway | `advanced-ai-model-lunar-ice-detection-production.up.railway.app` |
| Frontend (React) | Vercel | [advanced-ai-model-lunar-ice-detecti.vercel.app](https://advanced-ai-model-lunar-ice-detecti.vercel.app) |

Variáveis obrigatórias no Railway: `ENV=production`, `API_KEY`, `ALLOWED_ORIGINS`, `DATA_MODE=real`.
Variáveis obrigatórias no Vercel: `VITE_API_URL`, `VITE_API_KEY`. Root Directory: `frontend`.

**Docker (local):**
```bash
make build
docker-compose up
```

Os volumes `./data` e `./model` são montados no container — pesos (`pesos.pth`, `rl_pesos.pth`) e dados processados persistem entre rebuilds.

**Variáveis de ambiente:**

| Variável | Padrão | Descrição |
|---|---|---|
| `DATA_MODE` | `real` | `real` usa dados processados; `mock` usa grade 180×360 sintética |
| `TRAIN_EPOCHS` | `30` | Número de epochs do treino CNN |
| `ALLOWED_ORIGINS` | `*` | CORS origins separadas por vírgula |
| `VITE_API_URL` | `http://localhost:8000` | URL do backend para o frontend |

---

## Referências científicas

- Colaprete et al. (2010) *Science* 330 — LCROSS: confirmação de H₂O em Cabeus
- Paige et al. (2010) *Science* 330 — Diviner: temperaturas PSR, Hermite 26K
- Gladstone et al. (2010) *Science* 330 — LAMP: assinatura UV em Shackleton
- Spudis et al. (2010) *GRL* — Mini-RF: CPR > 1.0 como indicador de gelo
- Mazarico et al. (2011) *Icarus* 211 — LOLA: catálogo PSR e iluminação polar
- Vasavada et al. (2012) *JGR Planets* — perfil térmico subsuperficial lunar
- Hayne et al. (2015) *JGR Planets* — Diviner: mapa global de hidratação
- Williams et al. (2019) *JGR Planets* — Diviner EPF dataset
- Sato et al. (2014) *JGR Planets* — LROC WAC photometry global

---

## Citação

```bibtex
@software{almeida_da_silva_2026,
  author    = {Almeida da Silva, Yago},
  title     = {Lunar Ice Intelligence},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20014594},
  url       = {https://doi.org/10.5281/zenodo.20014594}
}
```

---

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
