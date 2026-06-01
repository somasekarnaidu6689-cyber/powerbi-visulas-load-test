FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEADLESS_BROWSER=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget \
        curl \
        gnupg2 \
        ca-certificates \
        fonts-liberation \
        libnss3 \
        libxss1 \
        libasound2 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libgtk-3-0 \
        libxshmfence1 \
        libxtst6 \
        libxi6 \
        libxcursor1 \
        chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r pbi_monitor/requirements.txt

EXPOSE 5000
CMD ["python", "pbi_monitor/app.py"]
