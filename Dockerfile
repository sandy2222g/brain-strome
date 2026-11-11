FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements.txt .
# The optional `cacert` secret lets the build work behind a TLS-intercepting proxy; normal builds ignore it.
RUN --mount=type=secret,id=cacert,required=false \
    if [ -f /run/secrets/cacert ]; then export PIP_CERT=/run/secrets/cacert; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY static ./static
COPY data ./data
RUN useradd -m app && chown -R app /app
USER app
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "uvicorn chorerota.api:app --host 0.0.0.0 --port ${PORT}"]
