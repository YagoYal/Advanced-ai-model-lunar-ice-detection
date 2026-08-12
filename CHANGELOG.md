# Changelog

Registro de mudanças significativas do projeto, por data. Formato livre inspirado em
[Keep a Changelog](https://keepachangelog.com/) — cada entrada tem evidência real
(comando rodado, teste passando, commit), não estimativa.

---

## 2026-08-12 — Deploy real, publicação acadêmica e triagem de dependências

Depois da auditoria de segurança do dia anterior ter corrigido o código em `main`
sem nunca chegar à produção, esta sessão fechou esse hiato e organizou a presença
acadêmica do projeto.

### Produção
- **Primeiro deploy real desde 1º de junho** (`flyctl deploy`, versão 6) — trouxe
  pra produção as correções de CVE, P3/P7 e o fix real de CI da sessão anterior,
  que estavam prontos em `main` mas nunca deployados.
- Verificado com requisições reais, não suposição: `GET /health` → `200`,
  `GET /v1/openapi.json` → `200`, `POST /analisar` sem `X-API-Key` → `403`
  (autenticação funcionando).
- `frontend/.gitignore` adicionado (ignora `.vercel/` local).

### Publicação científica
- `paper.pdf` recompilado do zero via Docker (`texlive/texlive:latest`) e
  comparado byte-a-byte com a versão anterior — confirma que o conteúdo já
  estava correto, só o timestamp local enganava.
- **Publicado como preprint separado no Zenodo**: DOI `10.5281/zenodo.21897740`
  (CC-BY 4.0), linkado ao DOI do software (`10.5281/zenodo.20014594`) via
  metadado "Is supplemented by"/"Is supplement to" nos dois registros.
- Sincronizado no ORCID: 2 *works* públicos (software + paper), o paper com
  identifier extra "Part of" apontando pro DOI do software.
- `CITATION.cff`, `21897740.bib` e badges/BibTeX do `README.md` atualizados
  com os dois DOIs.

### Auditoria Regra zero — achados reais no `roadmap.md`
- `roadmap.md` afirmava que o modelo em produção usa `FocalLoss(α=0.75, γ=2.0)`.
  Falso — `model/train.py` usa BCE ponderada desde que a Focal Loss foi
  removida por causar colapso degenerado de treino. Corrigido.
- Linha morta contradizendo o item de recompilação do PDF logo abaixo dela.
  Removida.
- "`fly deploy` pendente" já estava obsoleto no momento em que foi lido —
  corrigido pra refletir o deploy real feito nesta sessão.

### Triagem de dependências (15 PRs do Dependabot acumulados, 0 revisados)
Cada um avaliado por risco real (uso no código, testes, runtime), não só
"é dependência, mergeia":

**Mergeados** (12, todos com teste antes/depois):
- 5× GitHub Actions (`cache`, `checkout`, `setup-node`, `setup-python`,
  `docker/setup-buildx-action`) — só workflow de CI, sem impacto em app.
- `requests` 2.33.1→2.34.2, `setuptools` ≥70→≥84.0.0 — patches diretos.
- `@vitejs/plugin-react` 6.0.1→6.0.5 — patch, build+13 vitest confirmados.
- `astropy` 6.1.3→8.0.1 — só usa `astropy.io.fits` num script de ingestão
  manual (`parse_lamp.py`), não `coordinates`/`units` como a categorização
  inicial (por risco) supunha.
- `uvicorn` 0.32.0→0.52.1 — validado com servidor real rodando (não só
  `TestClient`): HTTP real + sessão WebSocket real contra `/ws/simular`.
- `Pillow` ≥11.0.0→≥12.3.0 — dependência transitiva, sem import direto no
  código do projeto.
- `recharts` 2.12.0→3.10.1 — sem conflito de peer dependency com React 18
  (diferente do que se esperava); build e 13/13 vitest passando. **Sem**
  verificação visual automatizada (headless Edge instável no sandbox Windows
  desta sessão) — recomendado olhar as seções Dados/Rover manualmente.

**Bloqueados de propósito, com motivo verificado** (não "medo de major"):
- `react` 18.3.1→19.2.8 — `npm install --dry-run` confirma `ERESOLVE`:
  `react-leaflet@4.2.1` e `framer-motion@11` exigem `react ^18.0.0`. Precisa
  upgrade coordenado (react-leaflet v5 + framer-motion v13 juntos), sessão
  própria com teste visual do mapa/rover.
- `jsdom` 29→30 e `@testing-library/jest-dom` 6→7 — `jsdom@30` exige Node
  `≥22.22.2`; o CI (`docker-ci.yml`) roda Node 20. Bloqueado até decisão de
  bumpar o Node do CI.

---

## 2026-08-11 — Auditoria de segurança completa (70 dias sem commit em `main`)

Projeto ficou sem commit em `main` de 2026-06-02 a 2026-08-11. Auditoria rodada
com evidência real (`npm audit`, `pip-audit`), não estimativa.

### Segurança
- Frontend: 4 vulnerabilidades HIGH (`nanoid`, `postcss`, `undici`, `vite`)
  corrigidas via `npm audit fix` — 0 vulnerabilidades depois.
- Backend: 12 CVEs conhecidas — a mais grave, `starlette==0.38.6` (9 CVEs),
  corrigida via `fastapi` 0.115.0→0.141.1 (resolve `starlette` 1.6.0).
  `requests` e `pytest` também atualizados.
- **Zero automação de segurança antes desta sessão** — adicionado
  `.github/dependabot.yml` (pip+npm+github-actions, semanal) e 2 steps novos
  em `docker-ci.yml` (`pip-audit --local`, `npm audit --audit-level=high`)
  que falham o build em vulnerabilidade HIGH+.
- 3 worktrees + branches órfãs de sessões de agente abandonadas, removidas.

### Ciência
- **P3** — `backend/test_integration_production.py`: testes HTTP/WebSocket
  reais contra produção (não mock). 7/7 endpoints públicos passando.
- **P7** — `model/cross_validate.py`: cross-validation por quadrante polar.
  Achado real e documentado honestamente no paper: o modelo **não generaliza**
  para quadrante polar nunca visto no treino (hold_sul F1=0.000 em 30/30
  épocas). Não invalida produção (split aleatório vê todas as latitudes) —
  é limitação de extrapolação documentada, não bug.
- Bug real achado e corrigido em `model/run_interpret.py`: nunca buscava
  insolação/temperatura reais por coordenada, inflando falsos positivos nos
  controles negativos do relatório P6.
- `paper.tex` sincronizado: benchmark 12/14→14/14 (estava desatualizado desde
  antes do fix de haversine), novas seções de interpretabilidade (P6) e
  limitação OOD (P7), 3 referências bibliográficas novas.

### CI — bug corrigido, mas o diagnóstico inicial estava errado
Um bug real de CI foi identificado e corrigido nesta data, mas o diagnóstico
original (grid mock 64×64 causando erro de bounds) estava **errado** — baseado
num arquivo local não versionado que não existe em CI de verdade. O
diagnóstico correto (`data/processed/lro/mock/` ausente causa fallback de
ruído aleatório, não erro de bounds) só foi confirmado e corrigido de verdade
na sessão seguinte (ver entrada 2026-08-12 do log de memória do projeto — a
correção real está refletida em `backend/test_api.py`/`pytest.ini`/
`docker-ci.yml` no estado atual do repositório, não numa entrada separada
deste changelog).
