FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
WORKDIR /app
ENV MIGRATOR_ROOT=/app
COPY pyproject.toml ./
COPY migrator ./migrator
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && pip install --no-cache-dir --no-deps .
COPY benchmark ./benchmark
COPY reports ./reports
COPY docs ./docs
RUN useradd --uid 1000 --create-home runner && mkdir artifacts && chown runner:runner artifacts
USER runner
EXPOSE 8000
CMD ["migrator", "serve", "--host", "0.0.0.0"]
