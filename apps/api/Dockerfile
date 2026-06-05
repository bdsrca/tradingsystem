FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY requirements.txt requirements-dev.txt ./
COPY apps/api ./apps/api
COPY infra ./infra
COPY packages ./packages
COPY workers ./workers

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-dev.txt

ENV PYTHONPATH=/app/apps/api:/app/packages/data:/app/packages/quant:/app/packages/agents:/app/packages/email:/app/workers/daily

EXPOSE 8000

CMD ["uvicorn", "trading_system_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
