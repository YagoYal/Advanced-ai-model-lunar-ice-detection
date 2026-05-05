# memory.md — estável (não apagar entre sessões)

## Projeto
Lunar Ice Intelligence — detecção de gelo lunar por IA com dados reais LRO.
Trajetória: protótipo → científico → missão real. Autor: Yago Almeida da Silva | ORCID: 0009-0007-0094-0915 | yagoalcontact@gmail.com

## Objetivo
CNN physics-informed (LunarCNN) + DQN rover autônomo + API + frontend interativo.
Labels sem circularidade (PSR geometry nunca usada como label direta).

## Stack
- Model: PyTorch | LunarCNN(CNNEncoder 64×64 + PhysicsEncoder input_dim=5 + FusionHead) + Double DQN
- Physics: physics.py — Stefan-Boltzmann, Vasavada 2012, z_skin=0.62m, features_subsolo 3 depths
- Data: numpy, rasterio, astropy | grade 180×360 (lat=i−90, lon=j−180)
- Backend: FastAPI+uvicorn+slowapi+pydantic | :8000 | X-API-Key auth | CSP/HSTS
- Frontend: React+Vite+Leaflet+recharts+framer-motion | :5173 | 8 sections
- Infra: Docker+GitHub Actions CI | pytest(15)+vitest(13)

## Arquitetura crítica
```
model/cnn.py          — CNNEncoder(64×64→4096→128) + PhysicsEncoder(5→32→64→64) + FusionHead(192→128→64→1)
model/physics.py      — Stefan-Boltzmann, perfil_subsolo T(z), features_subsolo[3], insolacao_dinamica
model/hybrid_model.py — prever_com_incerteza() MC Dropout 30 passes
model/train.py        — WeightedBCELoss, Adam lr=1e-3, CosineAnnealingLR, TRAIN_EPOCHS(default 30)
model/validate.py     — 6 PSRs benchmark
model/benchmark.py    — 14 locais; 64×64 + 5 features physics (corrigido 03/05/2026)
data/data_pipeline/
  dataset.py          — features(5,): [insol_norm,lat_norm,sub_0.1m,sub_0.5m,sub_1.0m]
  generate_labels.py  — PSR+EPF+CPR independentes (sem circularidade)
  coords.py           — fonte única grade↔graus: lat=i−90, lon=j−180
backend/main.py       — CORS *, ALLOWED_ORIGINS via env, /analisar→8 campos, API key auth
autonomy/
  rl_env.py           — obs_dim=6, bonus_subsolo=max(0,1−temp_sub_n)×0.4
  rl_agent.py         — Double DQN, obs_dim=6, MLP 6→128→128→4
  environment.py      — AmbienteLunar: arr_temp_subsolo
frontend/src/
  App.jsx             — landing page, 8 seções
  sections/           — Hero,Sobre,Arquitetura,Ciencia,Dados,Analise,Rover,Referencias
  services/api.js     — analisar(), simular(), analisarComMapa()
```

## Resultados modelo
- Dataset: 58.624 ex | 14.656 positivos (25%) | val_loss=0.0109 | F1=0.997 | Recall=1.000 | Acc=0.998
- Benchmark 14 locais: 12/14 (86%) | PSRs: 6/8 | Negativos: 6/6
- Falhas: Nobile(conf=0.75) e Amundsen(conf=0.70) — ausentes do Mini-RF CPR label set

## API /analisar (8 campos)
probabilidade_gelo, variancia, confianca, temperatura, temperatura_subsolo[3], insolacao, insolacao_atual, fase_lunar

## Decisões permanentes
- Licença: Apache 2.0 | NOTICE + CITATION.cff + paper.tex (preprint 10 págs, arXiv-ready)
- Labels: apenas instrumentos independentes — sem circularidade nunca
- CNNEncoder: input real = 64×64 (FC=64×8×8=4096→128); comentários antigos 32×32 corrigidos
- benchmark.py: 64×64 + 5 features (features_subsolo) — versão corrigida em 03/05/2026

## Regras permanentes
- NUNCA treinos em paralelo (Ryzen 9 7900)
- NUNCA tool calls em paralelo — 1 por vez, sequencial
- Porta 8000: matar via PowerShell netstat antes de reiniciar
- pip install: unset CURL_CA_BUNDLE e OPENSSL_CONF (PostgreSQL corrompe SSL no Windows)
- torch>=2.3.1 sem pinar versão
- MapContainer NÃO pode ser filho de motion.div | ClickHandler DEVE ser filho de MapContainer

## Referências científicas
Paige 2010 Science 330 | Vasavada 2012 JGR | Mazarico 2011 Icarus 211
Colaprete 2010 Science 330 | Spudis 2010 GRL | Gladstone 2010 Science 330
Williams 2019 JGR | Sato 2014 JGR | Hayne 2015 JGR | van Hasselt 2016 AAAI
