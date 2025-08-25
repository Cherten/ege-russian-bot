from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from database.models import User, UserWord, Word
from aiogram import Bot
from config import NOTIFICATION_HOURS
import asyncio
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

class NotificationService:
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_reminder_to_user(self, user_telegram_id: int, words_count: int):
        """Отправляет напоминание пользователю о необходимости повторить слова"""
        try:
            if words_count == 0:
                return
                
            notification_text = (
                f"🔔 <b>Время повторить слова!</b>\n\n"
                f"У вас есть <b>{words_count}</b> слов готовых к повторению.\n\n"
                f"💡 <b>Слова для повторения:</b>\n"
            )
            
            # Добавляем первые 5 слов в уведомление
            ready_words_query = select(Word).join(UserWord).where(
                UserWord.user_id == user.id,
                UserWord.next_repetition <= datetime.utcnow(),
                UserWord.is_learned == False
            ).limit(5)
            ready_words_result = await session.execute(ready_words_query)
            ready_words = ready_words_result.scalars().all()
            
            for word in ready_words:
                notification_text += f"• {word.word}\n"
            
            if words_count > 5:
                notification_text += f"... и еще {words_count - 5} слов\n"
            
            notification_text += "\nНачните тренировку, чтобы закрепить материал! 🎯"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")]
            ])
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=notification_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания пользователю {user_telegram_id}: {e}")
    
    async def get_users_for_reminder(self, session: Session) -> list:
        """Получает пользователей, которым нужно отправить напоминания"""
        current_time = datetime.utcnow()
        
        # Подзапрос для подсчета слов, готовых к повторению
        words_subquery = select(func.count(UserWord.id)).where(
            UserWord.user_id == User.id,
            UserWord.next_repetition <= current_time,
            UserWord.is_learned == False
        ).scalar_subquery()
        
        # Основной запрос пользователей с количеством слов для повторения
        query = select(
            User.telegram_id,
            words_subquery.label('words_count')
        ).where(
            User.is_active == True,
            User.notifications_enabled == True,
            words_subquery > 0
        )
        
        result = await session.execute(query)
        return result.all()
    
    async def send_daily_reminders(self, session: Session):
        """Отправляет ежедневные напоминания всем пользователям"""
        users_for_reminder = await self.get_users_for_reminder(session)
        
        logger.info(f"Отправка напоминаний {len(users_for_reminder)} пользователям")
        
        for user_telegram_id, words_count in users_for_reminder:
            await self.send_reminder_to_user(user_telegram_id, words_count)
            # Небольшая задержка между отправками для избежания rate limit
            await asyncio.sleep(0.1)
    
    async def send_custom_reminder(self, session: Session, user_telegram_id: int, message: str):
        """Отправляет кастомное напоминание конкретному пользователю"""
        try:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки кастомного напоминания: {e}")
    
    async def get_user_statistics_for_reminder(self, session: Session, user_id: int) -> dict:
        """Получает статистику пользователя для персонализированных напоминаний"""
        # Количество слов в личном словаре
        total_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user_id,
            UserWord.is_learned == False
        )
        total_words_result = await session.execute(total_words_query)
        total_words = total_words_result.scalar()
        
        # Количество слов готовых к повторению
        ready_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user_id,
            UserWord.next_repetition <= datetime.utcnow(),
            UserWord.is_learned == False
        )
        ready_words_result = await session.execute(ready_words_query)
        ready_words = ready_words_result.scalar()
        
        # Количество выученных слов
        learned_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user_id,
            UserWord.is_learned == True
        )
        learned_words_result = await session.execute(learned_words_query)
        learned_words = learned_words_result.scalar()
        
        return {
            'total_words': total_words,
            'ready_words': ready_words,
            'learned_words': learned_words
        }
    
    async def send_motivational_reminder(self, session: Session, user_telegram_id: int, user_id: int):
        """Отправляет мотивационное напоминание с персональной статистикой"""
        stats = await self.get_user_statistics_for_reminder(session, user_id)
        
        if stats['ready_words'] == 0:
            return
            
        progress_percentage = (stats['learned_words'] / (stats['learned_words'] + stats['total_words'])) * 100 if (stats['learned_words'] + stats['total_words']) > 0 else 0
        
        motivational_messages = [
            f"🌟 Отличная работа! Вы уже выучили {stats['learned_words']} слов!",
            f"📈 Ваш прогресс: {progress_percentage:.1f}% от всех изученных слов!",
            f"🎯 Осталось совсем немного - всего {stats['ready_words']} слов готовы к повторению!",
            f"💪 Каждое повторение приближает вас к цели!"
        ]
        
        import random
        motivation = random.choice(motivational_messages)
        
        message_text = (
            f"🔔 **Напоминание о повторении**\n\n"
            f"{motivation}\n\n"
            f"📚 Слов готово к повторению: **{stats['ready_words']}**\n"
            f"✅ Уже выучено: **{stats['learned_words']}**\n"
            f"📖 Всего в изучении: **{stats['total_words']}**\n\n"
            f"Начните тренировку, чтобы закрепить знания! 🚀"
        )
        
        await self.send_custom_reminder(session, user_telegram_id, message_text) 