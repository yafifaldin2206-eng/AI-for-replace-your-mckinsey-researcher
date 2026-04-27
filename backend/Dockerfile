FROM python:3.12-slim

WORKDIR /app

# System deps untuk Playwright & PDF processing
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgbm-dev \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv untuk dep management cepat
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system -e .

# Install Playwright browser
RUN playwright install chromium --with-deps

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
