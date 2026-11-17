FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install torch==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.lock
RUN useradd --uid 10001 --create-home worker && mkdir /cache && chown worker /cache
COPY app app
COPY tests tests
COPY pytest.ini .
USER worker
CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
