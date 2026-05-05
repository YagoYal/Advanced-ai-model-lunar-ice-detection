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
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

ENV DATA_MODE=real
ENV PYTHONPATH=/app
ENV LOG_LEVEL=info

EXPOSE 8000

CMD ["gunicorn", "backend.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "-"]
