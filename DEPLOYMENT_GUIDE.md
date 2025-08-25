# 🚀 Полная инструкция по развертыванию бота 24/7

## Вариант 1: Развертывание на VPS/VDS (Ubuntu) - Рекомендуется

### 1.1 Подготовка сервера

1. **Выберите хостинг-провайдера:**
   - Timeweb (от 190₽/мес)
   - Reg.ru (от 250₽/мес)
   - Beget (от 160₽/мес)
   - FirstVDS (от 100₽/мес)

2. **Подключитесь к серверу по SSH:**
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

3. **Запустите скрипт автоматической установки:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Или выполните ручную установку:**

#### Ручная установка:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3 python3-pip python3-venv git -y

# Создание пользователя для бота
sudo useradd -m -s /bin/bash bot
sudo usermod -aG sudo bot

# Переключение на пользователя bot
sudo su - bot

# Создание директории проекта
mkdir -p /home/bot/vocabulary-bot
cd /home/bot/vocabulary-bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.2 Загрузка файлов проекта

Загрузите все файлы проекта в `/home/bot/vocabulary-bot/` любым удобным способом:

1. **Через SCP:**
   ```bash
   scp -r * bot@YOUR_SERVER_IP:/home/bot/vocabulary-bot/
   ```

2. **Через Git (если используете репозиторий):**
   ```bash
   git clone https://github.com/yourusername/vocabulary-bot.git
   ```

3. **Через FTP/SFTP клиент** (FileZilla, WinSCP)

### 1.3 Настройка конфигурации

1. **Создайте файл .env:**
   ```bash
   cd /home/bot/vocabulary-bot
   nano .env
   ```

2. **Заполните переменные окружения:**
   ```env
   BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
   ADMIN_IDS=123456789,987654321
   DATABASE_URL=sqlite+aiosqlite:///./vocabulary_bot.db
   NOTIFICATION_HOURS=9,13,18
   ```

### 1.4 Настройка автозапуска через systemd

1. **Скопируйте service файл:**
   ```bash
   sudo cp vocabulary-bot.service /etc/systemd/system/
   ```

2. **Обновите systemd и запустите службу:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vocabulary-bot
   sudo systemctl start vocabulary-bot
   ```

3. **Проверьте статус:**
   ```bash
   sudo systemctl status vocabulary-bot
   ```

4. **Просмотр логов:**
   ```bash
   sudo journalctl -u vocabulary-bot -f
   ```

## Вариант 2: Развертывание через Docker

### 2.1 Установка Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose -y

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
```

### 2.2 Запуск через Docker Compose

1. **Создайте файл .env:**
   ```env
   BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
   ADMIN_IDS=123456789,987654321
   NOTIFICATION_HOURS=9,13,18
   ```

2. **Запустите контейнер:**
   ```bash
   docker-compose up -d
   ```

3. **Просмотр логов:**
   ```bash
   docker-compose logs -f vocabulary-bot
   ```

4. **Остановка:**
   ```bash
   docker-compose down
   ```

## Вариант 3: Облачные платформы

### 3.1 Heroku (Бесплатный план убран, но можно использовать платный)

1. Создайте Procfile:
   ```
   worker: python main.py
   ```

2. Установите переменные окружения в настройках Heroku

### 3.2 Railway

1. Подключите GitHub репозиторий
2. Установите переменные окружения
3. Выберите plan (от $5/мес)

### 3.3 Render

1. Создайте Web Service
2. Установите переменные окружения
3. Используйте бесплатный план с ограничениями

## Вариант 4: Домашний сервер (Raspberry Pi / старый ПК)

### 4.1 Подготовка

1. Установите Ubuntu Server или Raspberry Pi OS
2. Настройте статический IP
3. Настройте проброс портов (если нужен внешний доступ)

### 4.2 Установка

Следуйте инструкциям из Варианта 1

### 4.3 Настройка автозапуска при включении

```bash
# Добавьте в crontab
crontab -e

# Добавьте строку:
@reboot /home/bot/vocabulary-bot/start.sh
```

## Мониторинг и обслуживание

### Полезные команды для systemd:

```bash
# Запуск службы
sudo systemctl start vocabulary-bot

# Остановка службы
sudo systemctl stop vocabulary-bot

# Перезапуск службы
sudo systemctl restart vocabulary-bot

# Статус службы
sudo systemctl status vocabulary-bot

# Просмотр логов
sudo journalctl -u vocabulary-bot -f

# Просмотр последних 100 строк логов
sudo journalctl -u vocabulary-bot -n 100
```

### Резервное копирование базы данных:

```bash
# Создание бэкапа
cp /home/bot/vocabulary-bot/vocabulary_bot.db /home/bot/backups/vocabulary_bot_$(date +%Y%m%d_%H%M%S).db

# Автоматическое резервное копирование (добавьте в crontab)
0 2 * * * cp /home/bot/vocabulary-bot/vocabulary_bot.db /home/bot/backups/vocabulary_bot_$(date +\%Y\%m\%d_\%H\%M\%S).db
```

## Рекомендации по безопасности

1. **Используйте отдельного пользователя для бота**
2. **Регулярно обновляйте систему**
3. **Настройте firewall:**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   ```
4. **Не храните токены в открытом виде**
5. **Делайте регулярные бэкапы**

## Решение проблем

### Бот не запускается:
1. Проверьте логи: `sudo journalctl -u vocabulary-bot -f`
2. Убедитесь, что BOT_TOKEN корректный
3. Проверьте права доступа к файлам

### Бот падает:
1. Проверьте наличие всех зависимостей
2. Убедитесь в корректности базы данных
3. Проверьте доступность интернета

### База данных повреждена:
1. Восстановите из бэкапа
2. Или пересоздайте базу данных (потеря данных)

## Дополнительные возможности

### Настройка SSL/TLS сертификата (если нужен webhook):
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

### Настройка Nginx (если нужен веб-интерфейс):
```bash
sudo apt install nginx
# Настройте конфигурацию в /etc/nginx/sites-available/
```

Удачи с развертыванием! 🚀 