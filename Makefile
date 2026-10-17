PYTHON ?= python
export PYTHONPATH=backend:.

.PHONY: setup snapshot seed verify api test demo pdf pdfcheck

setup:
	$(PYTHON) -m pip install -r backend/requirements.txt

snapshot:
	$(PYTHON) pipelines/snapshot_feeds.py

seed:
	$(PYTHON) pipelines/seed_demo.py

verify:
	$(PYTHON) pipelines/verify_cache.py

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

test:
	pytest backend/tests

demo:
	$(PYTHON) pipelines/seed_demo.py && $(PYTHON) pipelines/verify_cache.py

pdf:
	$(PYTHON) pdf_generator/render.py --all-demo

pdfcheck:
	$(PYTHON) pdf_generator/render.py --all-demo --check
