FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy package source BEFORE pip install so setuptools can find `app/`
COPY pyproject.toml ./
COPY app ./app
COPY data ./data

RUN pip install --upgrade pip && pip install .

# Railway sets $PORT
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
