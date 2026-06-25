.PHONY: install seed run-api run-ui test clean

install:
	python -m pip install -r requirements.txt

seed:
	python -m app.db.seed

run-api:
	uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

run-ui:
	streamlit run ui/streamlit_app.py

test:
	pytest -q

clean:
	rm -rf .pytest_cache __pycache__ app/**/__pycache__ tests/**/__pycache__
