export PYTHONPATH=backend:.

.PHONY: setup snapshot seed verify api test demo

setup:
	pip install -r backend/requirements.txt

snapshot:
	python -m pipelines.snapshot_feeds

seed:
	python -m pipelines.seed_demo

verify:
	python -m pipelines.verify_cache

api:
	uvicorn app.main:app --app-dir backend --reload --port 8000

test:
	pytest backend/tests -q

demo: seed verify api
