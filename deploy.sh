#!/bin/bash

# Скрипт для развертывания телеграм бота на Ubuntu сервере

echo "🚀 Начинаем развертывание бота..."

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Установка Python 3.11+
echo "🐍 Установка Python..."
sudo apt install python3 python3-pip python3-venv git -y

# Создание пользователя для бота (опционально)
echo "👤 Создание пользователя bot..."
sudo useradd -m -s /bin/bash bot
sudo usermod -aG sudo bot

# Переключение на пользователя bot
sudo -u bot bash << 'EOF'
cd /home/bot

# Клонирование проекта (замените URL на ваш репозиторий)
echo "📥 Клонирование проекта..."
# git clone https://github.com/yourusername/vocabulary-bot.git
# cd vocabulary-bot

# Если проект уже загружен, создаем директорию
mkdir -p vocabulary-bot
cd vocabulary-bot

# Создание виртуального окружения
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip install --upgrade pip
pip install aiogram==3.7.0 aiofiles==23.2.1 sqlalchemy==2.0.23 alembic==1.12.1 apscheduler==3.10.4 python-dotenv==1.0.0 asyncpg==0.29.0 aiosqlite==0.19.0

# Создание .env файла
echo "⚙️ Настройка конфигурации..."
cat > .env << 'ENVEOF'
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///./vocabulary_bot.db
NOTIFICATION_HOURS=9,13,18
ENVEOF

echo "✅ Развертывание завершено!"
echo "❗ Не забудьте:"
echo "1. Обновить BOT_TOKEN в файле .env"
echo "2. Обновить ADMIN_IDS в файле .env"
echo "3. Скопировать файлы проекта в /home/bot/vocabulary-bot/"
EOF 