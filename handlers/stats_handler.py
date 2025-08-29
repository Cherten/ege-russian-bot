from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database.database import get_session
from database.models import User
from services.leveling_service import leveling_service

router = Router()

@router.message(F.text == "📊 Моя статистика")
async def show_user_stats(message: Message):
    """Показывает статистику пользователя"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Начните тренировку для создания профиля.")
            return
        
        # Формируем статистику
        stats_text = await leveling_service.format_user_stats(user, session)
        
        # Создаем клавиатуру с дополнительными опциями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Топ игроков", callback_data="show_leaderboard")],
            [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")]
        ])
        
        await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(F.text == "🏆 Рейтинг")
async def show_leaderboard_command(message: Message):
    """Показывает топ игроков по команде из меню"""
    await show_leaderboard_internal(message)

@router.callback_query(F.data == "show_leaderboard")
async def show_leaderboard_callback(callback):
    """Показывает топ игроков по callback"""
    await callback.answer()
    await show_leaderboard_internal(callback.message)

async def show_leaderboard_internal(message: Message):
    """Внутренняя функция для показа топа игроков"""
    async for session in get_session():
        # Получаем топ игроков
        leaderboard = await leveling_service.get_leaderboard(session, limit=10)
        
        if not leaderboard:
            await message.answer("📊 Рейтинг пока пуст. Станьте первым!")
            return
        
        # Формируем сообщение с рейтингом
        leaderboard_text = "🏆 <b>Топ игроков</b>\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user, level_name) in enumerate(leaderboard, 1):
            # Получаем медаль или номер места
            if i <= 3:
                place_icon = medals[i-1]
            else:
                place_icon = f"{i}."
            
            # Формируем имя пользователя
            user_name = user.first_name or user.username or f"Пользователь {user.id}"
            if len(user_name) > 20:
                user_name = user_name[:17] + "..."
            
            leaderboard_text += (
                f"{place_icon} <b>{user_name}</b>\n"
                f"    🏆 Уровень {user.level}: {level_name}\n"
                f"    ⭐ {user.experience_points} опыта\n\n"
            )
        
        # Добавляем информацию о текущем пользователе, если он не в топе
        current_user_id = message.from_user.id if hasattr(message, 'from_user') else message.message.from_user.id
        
        user_in_top = any(user.telegram_id == current_user_id for user, _ in leaderboard)
        
        if not user_in_top:
            user_query = select(User).where(User.telegram_id == current_user_id)
            user_result = await session.execute(user_query)
            current_user = user_result.scalar_one_or_none()
            
            if current_user:
                current_level_name = leveling_service.get_level_name(current_user.level)
                leaderboard_text += (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📍 <b>Ваше место:</b>\n"
                    f"🏆 Уровень {current_user.level}: {current_level_name}\n"
                    f"⭐ {current_user.experience_points} опыта"
                )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="show_my_stats")],
            [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")]
        ])
        
        await message.answer(leaderboard_text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "show_my_stats")
async def show_my_stats_callback(callback):
    """Показывает статистику пользователя по callback"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    async for session in get_session():
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return
        
        stats_text = await leveling_service.format_user_stats(user, session)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Топ игроков", callback_data="show_leaderboard")],
            [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")]
        ])
        
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "start_training")
async def start_training_callback(callback):
    """Перенаправляет к началу тренировки"""
    await callback.answer("Выберите 'Начать тренировку' в главном меню!")
    
    # Можно добавить более сложную логику для прямого запуска тренировки
    await callback.message.answer(
        "🎯 Для начала тренировки используйте кнопку <b>'🎯 Начать тренировку'</b> в главном меню",
        parse_mode="HTML"
    )
