# Lunar Ice Intelligence — Roadmap

> **Versão:** 1.0.0 · **DOI:** [10.5281/zenodo.20014594](https://doi.org/10.5281/zenodo.20014594) · **Última revisão:** 2026-08-12

---

## Fase 0 — Fundações científicas

- [x] Definir grade global 180×360 (1°/pixel)
- [x] Sistema de coordenadas único: `lat = i − 90`, `lon = j − 180` (`coords.py`)
- [x] Coletar referências científicas canônicas (Paige 2010, Vasavada 2012, Mazarico 2011, Sato 2014, Colaprete 2010, Spudis 2010, Williams 2019, Gladstone 2010)
- [x] Definir limiar de estabilidade do gelo: T < 110 K (Paige 2010)
- [x] Calcular profundidade de pele térmica: z_skin = 0.62 m (κ = 4.7×10⁻⁷ m²/s, P = 2.551×10⁶ s)

---

## Fase 1 — Pipeline de dados NASA

### Modelagem física
- [x] Stefan-Boltzmann para temperatura de superfície (`physics.py`)
- [x] Perfil subsuperficial T(z) exponencial — Vasavada 2012 (`perfil_subsolo`)
- [x] Insolação dinâmica por latitude e fase lunar (`insolacao_dinamica`)
- [x] Features subsuperficiais em 3 profundidades: 0.1 m, 0.5 m, 1.0 m (`features_subsolo`)
- [x] Grade temperatura superfície 180×360 → `temperatura.npy`
- [x] Grade insolação 180×360 → `insolacao.npy`
- [x] Grade subsuperficial 180×360×20 (0–2 m) → `temperatura_subsolo.npy`

### Integração de dados reais

- [x] Diviner: temperatura de brilho + EPF (medições diretas, conf=1.0)
- [x] LAMP UV: detecção Shackleton/Peary/Whipple (conf=0.9, via catálogo literatura)
- [x] Mini-RF CPR: threshold ≥ 0.25 → 4 002 pixels polares (97.9% em |lat|>70°, conf=0.8) — validado 2026-05-31
- [x] LCROSS: Cabeus (conf=1.0)
- [x] Labels sem circularidade: fontes físicas ≠ fontes de labels (`generate_labels.py`)
- [x] `labels_gelo.npy` + `labels_confianca.npy` (14 700 positivos, 25.4% com threshold≥0.25)
- [x] Modo mock: dados sintéticos para desenvolvimento sem NASA (`data/processed/lro/mock/`)

---

## Fase 2 — Modelo de IA

### Arquitetura LunarCNN
- [x] `CNNEncoder`: 3× Conv+BN+ReLU+MaxPool → 128 features (input 64×64)
- [x] `PhysicsEncoder`: MLP 5→32→64→64 → 64 features
- [x] `FusionHead`: 192D → camadas lineares → Sigmoid → probabilidade de gelo
- [x] MC Dropout: 30 passes forward para estimativa de incerteza (`prever_com_incerteza`)
- [x] Wrapper `modelo_hibrido()` + fase lunar (`tempo_lunar`)
- [x] Inferência ONNX Runtime em produção (`modelo_hibrido` usa ONNX; PyTorch preservado para MC Dropout)

### Treinamento
- [x] `LunarDataset`: 58 624 exemplos, 25% positivos, oversample 30% mínimo
- [x] Loss: `FocalLoss` (α=0.75, γ=2.0) — substituiu BCELoss
- [x] Otimizador: `AdamW` (lr=1e-3, weight_decay=1e-4)
- [x] Scheduler: `CosineAnnealingLR`
- [x] 30 épocas padrão (configurável via `TRAIN_EPOCHS`)
- [x] Resultados: val_loss=0.0294 · F1=0.991 · Recall=1.000
- [x] Pesos salvos: `model/pesos.pth` + `model/lunar_ice.onnx` (opset 17, dynamic batch)

### Validação científica
- [x] Benchmark em 14 PSRs conhecidos (LCROSS, LAMP, Diviner, Mini-RF)
- [x] Acurácia: **14/14 (100%)**
- [x] `validate.py` + `benchmark.py` com saída `benchmark_resultados.npy`

---

## Fase 3 — Navegação autônoma (RL)

### Ambiente MDP
- [x] `LunarRoverEnv` (obs_dim=6): [lat, lon, energia, insol, prob_gelo, temp_sub] normalizados
- [x] 4 ações: Norte, Sul, Oeste, Leste
- [x] Função de recompensa: `prob_gelo×2.0 + delta_ice×1.0 + bonus_novo×0.3 + bonus_subsolo×0.4 − custo×0.1`
- [x] Bônus subsuperficial: recompensa temperaturas frias em profundidade
- [x] Terminal: energia ≤ 0 ou 200 passos
- [x] `AmbienteLunar`: lookups O(1) via arrays numpy

### Agente DQN
- [x] Rede Q: MLP [6→128→128→64→4]
- [x] Double DQN: rede principal seleciona, rede target avalia
- [x] **Prioritized Experience Replay** (SumTree O(log N), α=0.6, β annealing 0.4→1.0, IS weights)
- [x] Soft update target: τ = 0.005
- [x] Gradiente clipping: max_norm=1.0
- [x] Loss: `SmoothL1Loss`
- [x] ε-greedy com decaimento exponencial (ε_start=1.0, ε_end=0.01, decay=5 000 steps)
- [x] Treinamento: 500 episódios · reward médio ~165.38 · ice_max=1.000
- [x] Pesos salvos: `model/rl_pesos.pth`

### Planejamento
- [x] `Planner` greedy como fallback ao DQN
- [x] Rover com longitude circular e latitude com clip
- [x] `strategy.py`: testa 4 direções, clipagem pelos limites reais H×W

---

## Fase 4 — Backend API

- [x] FastAPI + Uvicorn assíncrono
- [x] `POST /analisar` — retorna 8 campos: probabilidade_gelo, variancia, confianca, temperatura, temperatura_subsolo[3], insolacao, insolacao_atual, fase_lunar, altitude_m
- [x] `POST /analisar_com_mapa` — heatmap 5×5 de vizinhança
- [x] `POST /simular` — simulação greedy com até 100 passos
- [x] `WebSocket /ws/simular` — streaming passo-a-passo em tempo real
- [x] `POST /predict` — inferência direta (limite 4 096 elementos)
- [x] `GET /health` + `GET /`
- [x] Rate limiting via `slowapi`: 30 req/min (/analisar), 10 (/mapa), 20 (/simular)
- [x] Autenticação via `X-API-Key` (opcional dev, obrigatório produção)
- [x] Headers de segurança: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- [x] CORS configurável via `ALLOWED_ORIGINS`
- [x] Logging estruturado JSON (`_JsonFormatter`: ts, level, logger, msg, lat, lon, duration_ms)
- [x] Fallback automático para dados mock se reais ausentes
- [x] 25 testes de integração (`backend/test_api.py`)

---

## Fase 5 — Frontend

- [x] React 18.3.1 + Vite 8.0.0
- [x] 8 seções: Hero · Sobre · Arquitetura · Ciência · Dados · Análise · Rover · Referências
- [x] Mapa interativo Leaflet: clique → lat/lon → análise de gelo
- [x] Heatmap 5×5 de probabilidade
- [x] Visualização de trajetória do rover (`RoverPath.jsx`): Polyline + marcadores por probabilidade
- [x] Internacionalização i18n: Português (padrão) + English (`useT()`)
- [x] Animações com Framer Motion
- [x] **Cold start UX**: retry automático 3× (502/503/504) com backoff 4s · banner "⏳ Servidor acordando..."
- [x] **Polar heatmap**: 24 pontos (70/80/90° N+S × 4 longitudes) como CircleMarkers coloridos
- [x] **Share URL**: `?lat=&lon=` na URL · auto-análise ao abrir · copia para clipboard
- [x] **PWA**: service worker (cache-first assets, network-only API) · manifest.json · meta tags iOS
- [x] **Gráfico de convergência RL ao vivo**: appenda ponto após cada simulação (reward + ice_max reais)
- [x] **Comparação polar**: Peary vs. Shackleton (PSRs confirmados LAMP/Diviner)
- [x] `MapContainer` não aninhado em `motion.div` · `ClickHandler` filho direto de `MapContainer`
- [x] 14 testes vitest (api.js + RoverPath)

---

## Fase 6 — Infraestrutura e deploy

- [x] `Dockerfile`: `python:3.13-slim-bookworm`, usuário não-root, gunicorn+uvicorn
- [x] `docker-compose.yml`: volumes persistentes, healthcheck, variáveis de ambiente
- [x] GitHub Actions CI (`docker-ci.yml`): build Docker · pytest DATA_MODE=mock · validação científica · smoke test /health
- [x] Makefile: `build`, `run-real`, `run-mock`, `test`, `test-frontend`, `test-all`, `scan`
- [x] **Deploy backend: Fly.io** — `lunar-ice-api.fly.dev` · scale-to-zero · grace_period=45s · ONNX RT ativo
- [x] **Deploy frontend: Vercel** — `lunar-ice.vercel.app` · auto-deploy do GitHub main
- [x] GitHub → Vercel auto-deploy conectado (push → deploy automático)
- [x] Trivy security scan target (`make scan`)

---

## Fase 7 — Publicação acadêmica

- [x] `CITATION.cff` com 8 referências científicas e ORCID do autor
- [x] `paper.tex` + `paper.pdf` — manuscrito completo
- [x] `20014594.bib` — BibTeX para citação do software
- [x] Publicação Zenodo: **DOI 10.5281/zenodo.20014594** (v1.0.0, maio 2026, tipo Software)
- [x] ORCID: work adicionado (público) via DOI
- [x] GitHub: [YagoYal/Advanced-ai-model-lunar-ice-detection](https://github.com/YagoYal/Advanced-ai-model-lunar-ice-detection)
- [x] Apache 2.0 License + NOTICE

---

## Fase 8 — Próximos passos

### P1 — Dados reais de maior resolução (alto esforço, longo prazo)

- [ ] Usar dados Diviner EPF completos — atualmente integrados apenas os pontos próximos a Cabeus; expandir para toda a grade polar
- [ ] Integrar Mini-RF Level 2 de alta resolução (sub-pixel CPR real, não fração estimada)
- [ ] Integrar tiles LROC WAC 303ppd completos como feature de textura (sem ser label)
- [ ] LAMP espacial: geolocalização das masks 1D via SCUT_TIME + atitude da espaçonave

### P2 — Modelo e RL (médio prazo)

- [ ] Aumentar `obs_dim` do RL para incluir altimetria (LOLA) e CPR em tempo real (requer retreino)
- [ ] Treinar CNN com augmentation espacial (rotações polares — relevante para dados polares assimétricos)
- [ ] Resolução maior: 1°/px → 0.5°/px requer ~4× mais memória e retreino completo

### P3 — Backend e infraestrutura (baixa prioridade)

- [x] Testes de integração contra Fly.io produção — `backend/test_integration_production.py`
      (2026-08-11): HTTP real (não mock) contra `lunar-ice-api.fly.dev`. 7/7 endpoints
      públicos passando (health, status, docs, openapi, security headers, CORS, WebSocket
      `/ws/simular`). Endpoints autenticados (`/analisar`, `/predict`) cobertos no código mas
      pulados por padrão — rodar com `RUN_PROD_INTEGRATION=1 PROD_API_KEY=<key>` (key de
      produção não deve ir para o repo/chat). Desligado por padrão em CI (`RUN_PROD_INTEGRATION`
      não setado) para não depender de rede nem acordar o scale-to-zero a cada push.
- [ ] Cache Redis para `/analisar` — reduz latência após cold start para coordenadas populares
- [ ] Exportação de relatório PDF por coordenada

### P4 — Autonomia avançada (pesquisa)

- [ ] Planejamento multi-agente (múltiplos rovers cooperativos)
- [ ] Restrições de energia solar por terreno LOLA (iluminação real não-lambertiana)
- [ ] Comunicação com delay realista Terra-Lua (~1.3 s)

### P5 — Missão real (dependente de parceiros externos)

- [ ] Interface com protocolo SPICE/NAIF para ephemeris precisos
- [ ] Integração com simulador de rover (ROS 2 / Gazebo)
- [ ] Validação com dados da missão PRIME-1 / VIPER (quando disponíveis publicamente)
- [ ] Submissão como ferramenta auxiliar para missão Artemis III

### P6 — Interpretabilidade científica ✓

- [x] GradCAM sobre `CNNEncoder` — hook em `conv[10]` (ReLU 16×16×64), upsample 64×64 (`model/interpret.py`)
- [x] SHAP sobre `PhysicsEncoder` — `GradientExplainer` com wrapper de imagem zero; fallback gradient×input (`shap_attribution`)
- [x] Calibration plot: MC Dropout 30 passes, reliability diagram + ECE (`calibration_curve`)
- [x] Relatório automático por coordenada: `run_interpret.py` gera JSON + PNGs; `/analisar` retorna `physics_attribution` em tempo real

### P7 — Robustez e generalização (médio prazo)

- [x] Cross-validation por quadrante polar — `model/cross_validate.py` (2026-08-11), 30 épocas/fold,
      limiar |lat|>60°. **Achado: o modelo NÃO generaliza para quadrante polar nunca visto no treino.**
      `hold_sul` (treina sem lat≤−60°, valida nele): F1=0.000 em todas as 30 épocas — falha total.
      `hold_norte` (espelhado): instável, oscila entre F1≈0.76 e F1=0.000 repetidamente; o F1=0.731
      reportado veio de sorte de época (menor val_loss), não de convergência estável. Hipótese: `lat_norm`
      é uma das 5 features de input — o modelo provavelmente aprende algo próximo de lookup por latitude
      em vez de física transferível (insolação/temp. subsolo puros). **Não invalida produção** (treino
      com split aleatório vê todas as latitudes) — é limitação de extrapolação OOD documentada, não bug.
      Resultados completos: `model/cross_validation/results.json`. Decisão pendente: reportar como
      limitação no artigo vs. investir em mitigação antes da submissão (ver Fase 9).
- [ ] Teste de distribution shift: injetar erro sistemático de ±5K no Diviner e medir degradação de F1
- [x] Calibration curve (reliability diagram) para MC Dropout — já implementado no P6 (`model/interpret.py`
      `calibration_curve`, MC Dropout 30 passes + ECE) — item duplicado, referência cruzada apenas.

---

## Fase 9 — Da ferramenta para a ciência

- [x] `paper.tex` sincronizado com resultados atuais (2026-08-11, branch `feat/p7-cross-validation`):
      benchmark 12/14→14/14 (86%→100%) — número estava desatualizado, predatava o fix de haversine
      (commit `6949773`); parágrafo de falhas reescrito explicando a causa real em vez de só apagar;
      nova subseção "Interpretability and Calibration" com resultados reais de P6 (GradCAM, SHAP/gradiente,
      ECE=0.0905 via MC Dropout) — incluindo um bug real encontrado e corrigido no processo
      (`run_interpret.py` nunca buscava insolação/temperatura reais por coordenada, inflando falsos
      positivos nos controles negativos); nova subseção "Out-of-Distribution Generalisation" com o
      achado do P7 (falha de generalização em quadrante polar nunca visto). 3 referências bibliográficas
      novas (Selvaraju 2017, Lundberg & Lee 2017, Gal & Ghahramani 2016).
- [ ] **Recompilar `paper.pdf`** — sem compilador LaTeX local disponível nesta sessão; braces/citações
      checados manualmente mas o PDF publicado ainda reflete a versão antiga. Necessário antes de submeter.
- [x] **`paper.pdf` recompilado** (2026-08-11) — via Docker `texlive/texlive:latest`
      (sem LaTeX instalado localmente), 2 passes pdflatex, 12 páginas, sem erro/referência
      quebrada. `paper.pdf` é gitignored (build artifact) — regenerar localmente antes de
      qualquer submissão futura se `paper.tex` mudar de novo.
- [ ] Script reprodutível: gerar todos os plots do `paper.tex` a partir dos `.npy` locais (figura única por comando)
- [ ] Submissão do dataset para PDS (Planetary Data System NASA) — licença pública, citável independentemente do código
- [ ] Submissão de artigo: Icarus / JGR Planets / MNRAS (manuscrito e PDF prontos — falta revisão humana final e escolha do journal-alvo)

---

## Fase 10 — Auditoria de segurança (2026-08-11/12)

Projeto ficou sem commit em `main` por 70 dias (2026-06-02 → 2026-08-11). Auditoria
completa rodada com evidência real (`npm audit`, `pip-audit`), não estimativa —
tudo abaixo já mergeado e pushado em `main`.

- [x] Frontend: 4 vulnerabilidades HIGH (`nanoid`, `postcss`, `undici`, `vite`) —
      corrigidas via `npm audit fix`, 0 vulnerabilidades depois. Build + 13/13 testes confirmados.
- [x] Backend: 12 CVEs conhecidas — a mais grave, `starlette==0.38.6` (9 CVEs,
      dependência-núcleo do FastAPI que processa toda requisição HTTP), corrigida
      via `fastapi` 0.115.0→0.141.1 (resolve starlette 1.6.0). `requests` 2.32.3→2.33.1,
      `pytest` 8.3.3→9.0.3. 25/25 testes confirmados depois do upgrade.
- [x] **Dependabot configurado** (`.github/dependabot.yml`) — pip (raiz), npm
      (frontend/), github-actions — semanal. Antes: zero monitoramento automático.
- [x] **CI ganhou gates de segurança** — 2 steps novos em `docker-ci.yml`
      (`pip-audit --local`, `npm audit --audit-level=high`) que falham o build
      em vulnerabilidade HIGH+, antes do build Docker.
- [x] Limpeza: 3 worktrees + branches órfãs de sessões de agente abandonadas,
      removidas (zero commits únicos além de `main`).
- [x] **Bug de CI corrigido**: testes com coordenadas fixas de PSR real
      (Shackleton, equador) falhavam silenciosamente quando `docker-ci.yml` roda
      com `DATA_MODE=mock` (grid sintético 64×64 menor que as coordenadas do
      grid real 180×360) — provavelmente vermelho há semanas sem ninguém notar.
      Corrigido com skip condicional baseado no tamanho real do grid carregado.
- [ ] **Pendente do usuário**: `fly deploy` — os fixes de CVE já estão em `main`
      mas a produção (Fly.io) só os recebe depois de um redeploy manual.
- [ ] Majors de frontend não atualizados nesta rodada (React 19, framer-motion 13,
      react-leaflet 5, recharts 3) — risco/esforço maior, avaliar separadamente.

---

## Métricas de estado atual

| Componente | Estado | Métrica |
|---|---|---|
| LunarCNN | Produção | F1=0.991 · Recall=1.000 · val_loss=0.0294 · Focal Loss α=0.75 γ=2.0 |
| ONNX | Produção (Fly.io) | opset 17 · dynamic batch · inferência determinística |
| Validação PSR | Produção | **14/14 (100%)** |
| DQN Rover | Produção | 500 ep · PER SumTree · Double DQN · reward~165.38 · ice_max=1.000 |
| Backend API | Produção* | FastAPI 0.141.1 + Starlette 1.6.0 · 6 endpoints REST + WebSocket /ws/simular · /v1/docs · Fly.io scale-to-zero — *`fly deploy` pendente pra pegar fix de CVE (2026-08-12) |
| Frontend | Produção | React 18.3.1 · 8 seções · PT+EN · Cold start UX · PWA · Polar heatmap · Share URL · Live chart · 0 vulnerabilidades npm |
| Testes | Ativo | 25 pytest (2 com skip condicional em DATA_MODE=mock) + 13 vitest |
| Segurança | Ativo (2026-08-12) | Dependabot (pip+npm+actions) · CI falha em HIGH+ (`pip-audit`, `npm audit`) |
| CI/CD | Ativo | GitHub Actions + Docker + Vercel auto-deploy |
| Publicação | Publicado | DOI 10.5281/zenodo.20014594 · `paper.tex`/`paper.pdf` sincronizados (14/14, P6, P7) |
