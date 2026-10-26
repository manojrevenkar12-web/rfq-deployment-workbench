# The workbench in one image: the API, the console it serves, and the three simulated customers.
FROM node:22-slim AS console
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RDW_ROOT=/app RDW_DATA=/app/data RDW_WEB=/app/web/dist
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[postgres]"
COPY config ./config
COPY heldout ./heldout
COPY reports ./reports
COPY skills ./skills
COPY --from=console /web/dist ./web/dist
RUN rdw-sim --root /app && useradd --uid 10001 --no-create-home workbench && chown -R workbench /app/data
USER workbench
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["rdw", "serve", "--host", "0.0.0.0", "--port", "8000"]
