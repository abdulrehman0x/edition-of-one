PYTHON ?= python
export PYTHONPATH=backend:.

.PHONY: setup snapshot seed verify api test demo pdf pdfcheck learn simulate extras web-install web

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
learn:
	$(PYTHON) pipelines/learn.py
simulate:
	$(PYTHON) pipelines/simulate_readers.py
extras:
	$(PYTHON) pipelines/build_extras.py
web-install:
	cd frontend && npm install
web:
	cd frontend && npm run dev

# --- Edition of One: PDF targets (append to Makefile) ---
pdf:
	python -m pdf_generator.render --edition frontend/public/sample-edition.json --out out/sample.pdf

pdfcheck:
	python -m pdf_generator.render --all-demo
	@mkdir -p docs/samples
	@for f in out/*.pdf; do \
		[ -f "$$f" ] || continue; \
		name=$$(basename "$$f" .pdf); \
		pdfinfo "$$f" >/dev/null; \
		pdftoppm -r 60 -png -f 1 -l 1 "$$f" "docs/samples/$$name"; \
	done

.PHONY: pdf pdfcheck
