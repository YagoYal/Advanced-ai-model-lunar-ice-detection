IMAGE_NAME = lunar-backend

# ─── Dev local ────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev:
	./start.sh

dev-skip:
	./start.sh --skip-tests

stop:
	pkill -f "uvicorn backend.main" 2>/dev/null || true
	pkill -f "vite" 2>/dev/null || true
	@echo "Servidores encerrados."

# ─── Pipeline de IA ───────────────────────────────────────────────────────────

data:
	PYTHONPATH=. python -m data.data_pipeline.generate_scientific_data --modo ambos
	PYTHONPATH=. python -m data.data_pipeline.generate_labels

train:
	PYTHONPATH=. python -m model.train

train-rl:
	PYTHONPATH=. python -m autonomy.train_rl --episodios 500 --passos 150

validate:
	PYTHONPATH=. python -m model.validate

demo-rl:
	PYTHONPATH=. python -m autonomy.train_rl --demo

pipeline: data train validate

# ─── Download NASA ────────────────────────────────────────────────────────────

download-epf:
	PYTHONPATH=. python -m data.data_pipeline.download --diviner-epf

download-lamp:
	PYTHONPATH=. python -m data.data_pipeline.download --lamp

download-lola:
	PYTHONPATH=. python -m data.data_pipeline.download --lola-stream

download-lroc-polar:
	PYTHONPATH=. python -m data.data_pipeline.download --lroc-polar

download-all:
	PYTHONPATH=. python -m data.data_pipeline.download --tudo
	PYTHONPATH=. python -m data.data_pipeline.download --lroc-polar

# ─── Testes ───────────────────────────────────────────────────────────────────

test:
	PYTHONPATH=. python -m pytest backend/ -v --tb=short

test-frontend:
	cd frontend && npm run test:run

test-all: test test-frontend

# ─── Docker ───────────────────────────────────────────────────────────────────

build:
	docker build -t $(IMAGE_NAME) .

run-real:
	docker run -p 8000:8000 -e DATA_MODE=real $(IMAGE_NAME)

run-mock:
	docker run -p 8000:8000 -e DATA_MODE=mock $(IMAGE_NAME)

scan:
	trivy image $(IMAGE_NAME)

.PHONY: install dev dev-skip stop \
        data train train-rl validate demo-rl pipeline \
        download-epf download-lamp download-lola download-lroc-polar download-all \
        test test-frontend test-all \
        build run-real run-mock scan
