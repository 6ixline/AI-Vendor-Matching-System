.PHONY: help run test clean

help:
	@echo "Available commands:"
	@echo "  make run    - Start the FastAPI server"
	@echo "  make test   - Run verification"
	@echo "  make clean  - Clean cache files"

run:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	python verify_setup.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
