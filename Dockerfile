# syntax=docker/dockerfile:1

FROM python:3.11-slim

# System deps for Chrome + Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (stable)
RUN set -eux; \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends google-chrome-stable; \
    rm -rf /var/lib/apt/lists/*

# webdriver-manager cache inside container (mountable)
# default state file location (mount ./data to persist)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    WDM_LOCAL=1 \
    WDM_CACHE_DIR=/home/appuser/.wdm \
    STATE_FILE=/app/data/state.json

WORKDIR /app

# Install Python deps
COPY pyproject.toml uv.lock README.md /app/
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir .

# Copy source
COPY visabot /app/visabot
COPY main.py /app/main.py

# Data dir for state/debug artifacts
RUN mkdir -p /app/data /home/appuser/.wdm

# A non-root user is nicer for hosted environments
RUN useradd -m -u 10001 appuser \
    && chown -R appuser:appuser /app /home/appuser
USER appuser

CMD ["python", "main.py"]
