FROM python:3.13-slim-bookworm

WORKDIR /app

# Atualiza pacotes do sistema para eliminar CVEs conhecidas na imagem base
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

COPY --chown=appuser:appuser requirements.txt .
# torch só-CPU: a VM do Fly não tem GPU, e o wheel padrão do PyPI para Linux
# traz CUDA (~514 MB de torch + mais de 1 GB de libs NVIDIA). Instalado antes
# do requirements.txt, ele já satisfaz `torch>=...` e o pip não baixa o de CUDA.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

ENV DATA_MODE=real
ENV PYTHONPATH=/app
ENV LOG_LEVEL=info

EXPOSE 8000

# exec: gunicorn vira o PID 1 e recebe o SIGTERM do Fly direto (desligamento
# limpo). Fica em forma de shell para expandir ${PORT}.
CMD exec gunicorn backend.main:app \
    -w 1 \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --timeout 120 \
    --log-level info \
    --access-logfile -
