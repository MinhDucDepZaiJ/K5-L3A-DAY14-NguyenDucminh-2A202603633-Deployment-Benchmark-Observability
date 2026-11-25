FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system agent && useradd --system --gid agent agent
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app/ app/
COPY utils/ utils/
USER agent
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=2)"
CMD ["sh", "-c", "export PORT=${PORT:-8000}; exec python -m app.server"]
