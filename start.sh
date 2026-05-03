#!/usr/bin/env bash
# start.sh — Lunar Ice Intelligence
#
# Uso:
#   ./start.sh                  # instala deps, verifica modelo, sobe backend + frontend
#   ./start.sh --skip-tests     # pula testes, sobe direto
#   ./start.sh --only-tests     # apenas testes, sem subir servidores
#   ./start.sh --train          # gera dados + labels + treina modelo CNN
#   ./start.sh --train-rl       # treina agente RL do rover
#   ./start.sh --validate       # roda validacao cientifica em PSRs conhecidos
#   ./start.sh --full           # tudo: dados -> labels -> treino -> validacao -> servidores

set -e

# ─── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${CYAN}[lunar]${NC} $1"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $1"; }
fail()  { echo -e "${RED}[erro]${NC}  $1"; exit 1; }
step()  { echo -e "\n${BLUE}━━━ $1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── Flags ────────────────────────────────────────────────────────────────────
SKIP_TESTS=false
ONLY_TESTS=false
DO_TRAIN=false
DO_TRAIN_RL=false
DO_VALIDATE=false
DO_FULL=false

for arg in "$@"; do
  case $arg in
    --skip-tests) SKIP_TESTS=true ;;
    --only-tests) ONLY_TESTS=true ;;
    --train)      DO_TRAIN=true ;;
    --train-rl)   DO_TRAIN_RL=true ;;
    --validate)   DO_VALIDATE=true ;;
    --full)       DO_FULL=true ; DO_TRAIN=true ; DO_TRAIN_RL=true ; DO_VALIDATE=true ;;
  esac
done

mkdir -p logs

# ─── Pré-requisitos ───────────────────────────────────────────────────────────
step "Verificando ambiente"
command -v python >/dev/null 2>&1 || fail "Python nao encontrado. Instale Python 3.10+"
command -v node   >/dev/null 2>&1 || fail "Node.js nao encontrado. Instale Node 18+"
command -v npm    >/dev/null 2>&1 || fail "npm nao encontrado."

PYTHON_VERSION=$(python --version 2>&1)
NODE_VERSION=$(node --version)
ok "$PYTHON_VERSION | Node $NODE_VERSION"

# ─── Dependências Python ──────────────────────────────────────────────────────
log "Instalando dependencias Python..."
# Limpa certificados inválidos injetados pelo PostgreSQL no ambiente Windows
unset REQUESTS_CA_BUNDLE
unset SSL_CERT_FILE
unset CURL_CA_BUNDLE
unset OPENSSL_CONF
pip install -r requirements.txt -q --disable-pip-version-check
ok "Python deps ok"

# ─── Dependências Node ────────────────────────────────────────────────────────
log "Instalando dependencias frontend..."
(cd frontend && npm install --silent)
ok "Node deps ok"

# ─── Pipeline de dados (se --train ou --full) ─────────────────────────────────
if [ "$DO_TRAIN" = true ]; then

  step "Pipeline de Dados Cientificos"

  # Dados reais (Diviner + LOLA model)
  if [ ! -f "data/processed/lro/temperatura.npy" ] || \
     [ "$(python -c "import numpy as np; a=np.load('data/processed/lro/temperatura.npy'); print(a.size)" 2>/dev/null)" = "0" ]; then
    log "Gerando dados cientificos (modelo Diviner/LOLA)..."
    PYTHONPATH="$(pwd)" python -m data.data_pipeline.generate_scientific_data --modo ambos \
      > logs/generate_data.log 2>&1 && ok "Dados gerados" || {
      warn "Erro ao gerar dados. Veja logs/generate_data.log"
    }
  else
    ok "Dados ja existem (data/processed/lro/)"
  fi

  # Labels PSR independentes
  log "Gerando labels PSR (independentes dos inputs)..."
  PYTHONPATH="$(pwd)" python -m data.data_pipeline.generate_labels \
    > logs/generate_labels.log 2>&1 && ok "Labels gerados" || {
    warn "Erro ao gerar labels. Veja logs/generate_labels.log"
  }

  step "Treinamento CNN (LunarCNN)"
  log "Iniciando treino... (pode levar varios minutos)"
  PYTHONPATH="$(pwd)" python -m model.train 2>&1 | tee logs/train.log

  if [ -f "model/pesos.pth" ]; then
    ok "Modelo treinado: model/pesos.pth"
  else
    warn "Arquivo model/pesos.pth nao encontrado. Verifique logs/train.log"
  fi
fi

# ─── Treinamento RL (se --train-rl ou --full) ─────────────────────────────────
if [ "$DO_TRAIN_RL" = true ]; then

  step "Treinamento RL do Rover (DQN)"
  log "Iniciando treino RL (500 episodios)..."
  PYTHONPATH="$(pwd)" python -m autonomy.train_rl --episodios 500 --passos 150 \
    2>&1 | tee logs/train_rl.log

  if [ -f "model/rl_pesos.pth" ]; then
    ok "Agente RL treinado: model/rl_pesos.pth"
  else
    warn "Arquivo model/rl_pesos.pth nao encontrado."
  fi
fi

# ─── Validacao cientifica (se --validate ou --full) ───────────────────────────
if [ "$DO_VALIDATE" = true ]; then

  step "Validacao Cientifica (PSRs conhecidos)"
  if [ ! -f "model/pesos.pth" ]; then
    warn "Modelo nao encontrado. Rode ./start.sh --train primeiro."
  else
    PYTHONPATH="$(pwd)" python -m model.validate 2>&1 | tee logs/validate.log
  fi
fi

# ─── Testes ───────────────────────────────────────────────────────────────────
if [ "$SKIP_TESTS" = false ]; then

  step "Testes Backend (pytest)"
  PYTHONPATH="$(pwd)" python -m pytest backend/ -v --tb=short || fail "Testes backend falharam."
  ok "Backend: testes passaram"

  step "Testes Frontend (vitest)"
  (cd frontend && npm run test:run) || fail "Testes frontend falharam."
  ok "Frontend: testes passaram"
fi

if [ "$ONLY_TESTS" = true ]; then
  echo ""
  ok "Testes concluidos. Encerrando (--only-tests)."
  exit 0
fi

# ─── Verificar modelo antes de subir ──────────────────────────────────────────
if [ ! -f "model/pesos.pth" ]; then
  warn "Modelo CNN nao treinado (model/pesos.pth ausente)."
  warn "O sistema rodara com pesos aleatorios."
  warn "Para treinar: ./start.sh --train"
fi

# ─── Iniciar Backend ──────────────────────────────────────────────────────────
step "Iniciando Servidores"
log "Iniciando backend (porta 8000)..."
PYTHONPATH="$(pwd)" uvicorn backend.main:app --reload --port 8000 \
  > logs/backend.log 2>&1 &
BACKEND_PID=$!

for i in {1..20}; do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    ok "Backend ativo (PID $BACKEND_PID)"
    break
  fi
  if [ "$i" -eq 20 ]; then
    fail "Backend nao respondeu em 20s. Veja logs/backend.log"
  fi
  sleep 1
done

# ─── Iniciar Frontend ─────────────────────────────────────────────────────────
log "Iniciando frontend (porta 5173)..."
(cd frontend && npm run dev > ../logs/frontend.log 2>&1) &
FRONTEND_PID=$!
sleep 3
ok "Frontend ativo (PID $FRONTEND_PID)"

# ─── Banner final ─────────────────────────────────────────────────────────────
MODEL_STATUS="sem pesos (aleatório)"
[ -f "model/pesos.pth"    ] && MODEL_STATUS="CNN treinado"
[ -f "model/rl_pesos.pth" ] && MODEL_STATUS="$MODEL_STATUS + RL rover"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Lunar Ice Intelligence — rodando                              ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Backend   ${CYAN}http://localhost:8000${NC}  (Swagger: /docs)"
echo -e "  Frontend  ${CYAN}http://localhost:5173${NC}"
echo -e "  Modelo    ${YELLOW}$MODEL_STATUS${NC}"
echo ""
echo -e "  Logs:"
echo -e "    ${YELLOW}logs/backend.log${NC}   ${YELLOW}logs/frontend.log${NC}"
echo -e "    ${YELLOW}logs/train.log${NC}     ${YELLOW}logs/train_rl.log${NC}"
echo ""
echo -e "  Comandos uteis:"
echo -e "    Treinar modelo:    ${CYAN}./start.sh --train${NC}"
echo -e "    Treinar rover RL:  ${CYAN}./start.sh --train-rl${NC}"
echo -e "    Validar modelo:    ${CYAN}./start.sh --validate${NC}"
echo -e "    Pipeline completo: ${CYAN}./start.sh --full${NC}"
echo -e "    Demo rover RL:     ${CYAN}python -m autonomy.train_rl --demo${NC}"
echo -e "    Dados NASA (LAMP): ${CYAN}python data/raw/lro/lamp/parse_lamp.py${NC}"
echo ""
echo -e "  Pressione ${RED}Ctrl+C${NC} para encerrar."
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ─── Cleanup ──────────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  log "Encerrando servidores..."
  kill "$BACKEND_PID"  2>/dev/null && ok "Backend encerrado"
  kill "$FRONTEND_PID" 2>/dev/null && ok "Frontend encerrado"
  exit 0
}
trap cleanup INT TERM

wait
