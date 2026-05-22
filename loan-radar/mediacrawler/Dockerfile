ARG PYTHON_IMAGE=m.daocloud.io/docker.io/library/python:3.11.10-slim-bookworm
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    DEBIAN_FRONTEND=noninteractive

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    nodejs \
    npm \
    libxkbcommon0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt || \
    (pip install --no-cache-dir fastapi uvicorn httpx pydantic python-dotenv aiofiles aiosqlite typer opencv-python playwright tenacity Pillow parsel && \
     python -m playwright install chromium)

RUN python -m playwright install chromium && \
    python -m playwright install-deps chromium

COPY . .

RUN mkdir -p data

EXPOSE 8080

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
