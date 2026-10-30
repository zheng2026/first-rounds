FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY tools/ tools/
COPY design/ design/
# No .env is copied. Pass NEBIUS_API_KEY, NEBIUS_BASE_URL (and optionally PRIVATE_NAMES, NTFY_TOPIC, FR_DB) as environment variables.
ENV FR_DB=/srv/data/firstrounds.sqlite
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
