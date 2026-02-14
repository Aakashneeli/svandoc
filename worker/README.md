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

## Placeholder

Implementation starts in `T-020` and related tasks.
