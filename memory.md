# memory.md — Lunar Ice Intelligence (estável)

## Projeto
Detecção de gelo lunar via CNN+física subsuperficial+RL. Trajetória: Protótipo→Científico→Missão real.
PATH: `Users\Usuario\Desktop\All\Projects\Advanced-ai-model-lunar-ice-detection\`

## Stack
| Camada | Tecnologia |
|---|---|
| Model | PyTorch · LunarCNN(CNNEncoder+PhysicsEncoder input_dim=5+FusionHead) · DQN Double Q-learning |
| Physics | physics.py · Stefan-Boltzmann · Vasavada 2012 · z_skin=0.62m |
| Data | NumPy · Rasterio · Astropy · LROC WAC · Diviner EPF · Mini-RF CPR · LAMP UV |
| Backend | FastAPI · Uvicorn/Gunicorn · Slowapi · Pydantic · :8000 |
| Frontend | React+Vite 8 · Leaflet · Recharts · Framer Motion · :5173 |
| Infra | Docker · GitHub Actions CI · pytest (backend) · vitest (frontend) |

## Arquitetura (arquivos críticos)
```
model/physics.py          — Stefan-Boltzmann, perfil_subsolo T(z), features_subsolo, insolacao_dinamica
model/cnn.py              — LunarCNN: CNNEncoder + PhysicsEncoder(input_dim=5) + FusionHead
model/hybrid_model.py     — modelo_hibrido(), prever_com_incerteza() MC Dropout 30 passes
model/train.py            — EPOCHS via env TRAIN_EPOCHS (default 30)
model/validate.py         — 6 PSRs benchmark
data/data_pipeline/
  dataset.py              — features(5,): [insol_norm, lat_norm, sub_0.1m, sub_0.5m, sub_1.0m]
  generate_scientific_data.py — temperatura_subsolo.npy (180,360,20)
  generate_labels.py      — PSR+EPF+CPR independentes (sem circularidade)
  coords.py               — fonte única grade↔graus: lat=i−90, lon=j−180
backend/main.py           — CORS, slowapi, SecurityHeadersMiddleware, API key auth, /analisar→8 campos
backend/.env.example      — ENV, API_KEY, ALLOWED_ORIGINS, DATA_MODE
autonomy/
  rl_env.py               — obs_dim=6, bonus_subsolo=max(0,1−temp_sub_n)×0.4
  rl_agent.py             — DQN Double Q-learning, obs_dim=6
  environment.py          — AmbienteLunar: arr_temp_subsolo, get_dados_subsolo(), clip get_dados()
  rover.py                — clip lat/lon mover(), longitude circular
frontend/src/
  LandingPage.jsx         — raiz da landing page
  sections/               — 8 seções: hero, sobre, arquitetura, ciencia, dados, analise, rover, referencias
  services/api.js         — analisar(signal), simular(), analisarComMapa() + AbortController
  components/Navbar.jsx   — hamburger responsivo, fecha ao rolar, z-index 1100
  components/ScrollToTop.jsx — visível após 300px, z-index 1050
  components/RoverPath.jsx
  leafletFix.js           — iconRetinaUrl + dimensões explícitas (fix Opera GX)
```

## Dados permanentes
- Grade: 180×360 (1°/px) | lat=i−90 | lon=j−180
- PSRs confirmados: 11 (LCROSS, LAMP, Diviner, Mini-RF) | Gelo estável: <110K (Paige 2010)
- z_skin=0.62m (√(κ·P/π), κ=4.7e-7 m²/s, P=2.551e6s)
- LROC tiles: LRO_WAC_Mosaic_Global_303ppd_v02 (303ppd correto; minZoom=1 maxZoom=7)
- Dataset: 58.624 exemplos | 14.656 positivos (25%) | F1=0.997 | val_loss=0.0101 | recall=1.000

## API /analisar (8 campos)
`probabilidade_gelo, variancia, confianca, temperatura, temperatura_subsolo[3], insolacao, insolacao_atual, fase_lunar`

## Fórmulas implementadas
| Fórmula | Arquivo |
|---|---|
| T = (S·(1−α)·cos(θ)/εσ)^0.25 | physics.py:temperatura_superficie |
| z_skin = √(κ·P/π) = 0.62m | physics.py:Z_SKIN |
| T(z) = T̄ + (Tsup−T̄)·exp(−z/z_skin) | physics.py:perfil_subsolo |
| E(lat,t) = 1361·max(0,cos(lat)·cos(2πt)) | physics.py:insolacao_dinamica |
| (μ,σ²) = f(x, N=30) MC Dropout | hybrid_model.py:prever_com_incerteza |
| R = prob×2 + Δice×1 + exp×0.3 + sub×0.4 − custo×0.1 | rl_env.py:step |

## Regras permanentes
- Labels: PSRs confirmados por instrumento independente — sem circularidade nunca
- NUNCA treinos em paralelo (Ryzen 9 7900; cancelar jobs background antes de novo treino)
- NUNCA tool calls em paralelo — 1 por vez, sequencial
- Porta 8000: matar via PowerShell netstat antes de reiniciar
- pip install: unset CURL_CA_BUNDLE e OPENSSL_CONF (PostgreSQL corrompe SSL no Windows)
- torch sem pinar versão (Python 3.13 requer ≥2.6)
- MapContainer NÃO pode ser filho de motion.div (quebra resize Leaflet)
- ClickHandler(useMapEvents) DEVE ser filho de MapContainer
- Respostas diretas; sem resumo pós-edição (usuário lê o diff)
- "pra já" = aplicar imediatamente sem análise prolongada
- Nunca criar *.md sem pedido explícito

## Referências científicas
Paige 2010 Science 330 | Vasavada 2012 JGR Planets | Mazarico 2011 Icarus 211
Sato 2014 JGR Planets | Williams 2019 | Colaprete 2010 Science 330
Spudis 2010 GRL | Gal & Ghahramani 2016 ICML
