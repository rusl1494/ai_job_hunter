# 1. Берем базу Python 3.11 (Linux Debian 12)
FROM python:3.11-slim

# 2. Устанавливаем системные утилиты
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libcups2 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Установка Google Chrome (ПРЯМАЯ ЗАГРУЗКА .DEB)
# Это обходит проблему с apt-key
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

# 4. Настройка рабочей папки
WORKDIR /app

# 5. Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь код
COPY . .

# 7. Переменная для Headless режима
ENV IN_DOCKER=true

# 8. Команда запуска
CMD ["python", "scraper_indeed.py"]