# Worker Package

This package will host asynchronous document processing workers.

## Planned responsibilities

1. Consume queued document processing jobs.
2. Run preprocessing and OCR model routing.
3. Normalize output into canonical schemas.
4. Persist extraction results and confidence maps.

## Planned stack

- Python 3.11
- Celery
- Redis
- vLLM client integrations

## Current status

1. Celery worker bootstrap is integrated in `T-018`.
2. Queue tasks are currently placeholder processing stubs until `T-020+`.
3. Local worker start script supports `WORKER_START_MODE=celery`.
