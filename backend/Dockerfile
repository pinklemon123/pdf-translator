FROM python:3.11-slim

# Install system deps required for some Python packages (OpenCV, Pillow, easyocr)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    git \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Use pip to install requirements
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

ENV PYTHONUNBUFFERED=1

# Create a non-root user for better security
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser \
 && chown -R appuser:appuser /app

USER appuser

# Expose default port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
FROM python:3.11-slim

# ==== 可选：接收构建期代理（build-args） ====
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 让 apt/pip 在构建阶段也用到代理（如果传了的话）
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgl1 libglib2.0-0 mupdf-tools \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip \
 && pip config set global.timeout 120 \
 && pip install -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

