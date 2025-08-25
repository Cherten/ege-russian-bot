import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "")

# База данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///vocabulary_bot.db")

# Настройки тренировки
WORDS_PER_TRAINING = 25

# Типы морфем
MORPHEME_TYPES = {
    'roots': 'Корни',
    'prefixes': 'Приставки', 
    'endings': 'Окончания',
    'spelling': 'Слитное, раздельное, дефисное написание',
    'n_nn': 'Н и НН',
    'suffix': 'Суффиксы',
    'stress': 'Ударения',
    'ne_particle': 'Частица НЕ'
}

# Интервалы повторений по кривой Эббингауза (в минутах)
REPETITION_INTERVALS = [
    20,        # 20 минут
    60,        # 1 час  
    540,       # 9 часов
    1440,      # 1 день
    2880,      # 2 дня
    8640,      # 6 дней
    44640      # 31 день
]

# Настройки уведомлений
NOTIFICATION_HOURS = [9, 14, 19]  # Время отправки напоминаний 