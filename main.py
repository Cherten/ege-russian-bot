import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN, NOTIFICATION_HOURS
from database.database import init_db, get_session
from handlers import training_handler, basic_handlers, admin_handler, stats_handler
from services.notification_service import NotificationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()
notification_service = None

async def set_bot_commands():
    """Устанавливает команды бота"""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="training", description="🎯 Начать тренировку"),
        BotCommand(command="dictionary", description="📚 Мой словарь"),
        BotCommand(command="statistics", description="📊 Статистика обучения"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="admin", description="👨‍💼 Админ-панель (только для админа)"),
        BotCommand(command="user_stats", description="👥 Статистика пользователей (админ)"),
        BotCommand(command="word_stats", description="📚 Статистика слов (админ)"),
        BotCommand(command="delete_word", description="🗑️ Удалить слово (админ)")
    ]
    await bot.set_my_commands(commands)

def get_main_keyboard():
    """Создает главную клавиатуру"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Начать тренировку")],
            [KeyboardButton(text="📚 Мой словарь"), KeyboardButton(text="📊 Моя статистика")],
            [KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

async def send_notifications():
    """Функция для отправки напоминаний"""
    try:
        async for session in get_session():
            await notification_service.send_daily_reminders(session)
            logger.info("Напоминания отправлены успешно")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}")

async def setup_scheduler():
    """Настройка планировщика задач"""
    global notification_service
    notification_service = NotificationService(bot)
    
    # Добавляем задачи для отправки напоминаний в указанные часы
    for hour in NOTIFICATION_HOURS:
        scheduler.add_job(
            send_notifications,
            trigger=CronTrigger(hour=hour, minute=0),
            id=f"reminder_{hour}",
            replace_existing=True
        )
        logger.info(f"Планировщик: напоминания будут отправляться в {hour}:00")
    
    scheduler.start()
    logger.info("Планировщик задач запущен")

async def startup():
    """Функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Установка команд бота
    await set_bot_commands()
    logger.info("Команды бота установлены")
    
    # Настройка планировщика
    await setup_scheduler()
    
    logger.info("Бот успешно запущен!")

async def shutdown():
    """Функция завершения работы бота"""
    logger.info("Завершение работы бота...")
    
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик задач остановлен")
    
    await bot.session.close()
    logger.info("Бот остановлен")

async def main():
    """Главная функция"""
    # Регистрация обработчиков
    dp.include_router(basic_handlers.router)
    dp.include_router(training_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(stats_handler.router)
    
    # Регистрация функций startup и shutdown
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    
    try:
        # Запуск polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Принудительное завершение работы") 