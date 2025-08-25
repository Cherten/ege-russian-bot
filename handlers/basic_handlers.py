from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, func
from database.database import get_session
from database.models import User, UserWord, TrainingSession, Word
from datetime import datetime, timedelta

router = Router()

async def generate_user_statistics(user_id: int, days: int = None):
    """Генерирует статистику пользователя за определенный период
    
    Args:
        user_id: ID пользователя  
        days: Количество дней для фильтрации (None = за все время)
    
    Returns:
        tuple: (stats_text, period_name)
    """
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return "❌ Пользователь не найден.", ""
        
        # Определяем период для фильтрации
        period_filter = None
        period_name = ""
        if days is not None:
            period_start = datetime.utcnow() - timedelta(days=days)
            period_filter = TrainingSession.created_at >= period_start
            period_name = f"за {days} дн."
        else:
            period_name = "за все время"
        
        # Статистика по словам (всегда за все время, так как это текущее состояние)
        total_words_query = select(func.count(UserWord.id)).where(UserWord.user_id == user.id)
        total_words_result = await session.execute(total_words_query)
        total_words = total_words_result.scalar()
        
        learned_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user.id,
            UserWord.is_learned == True
        )
        learned_words_result = await session.execute(learned_words_query)
        learned_words = learned_words_result.scalar()
        
        ready_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user.id,
            UserWord.next_repetition <= datetime.utcnow(),
            UserWord.is_learned == False
        )
        ready_words_result = await session.execute(ready_words_query)
        ready_words = ready_words_result.scalar()
        
        # Статистика по тренировкам за выбранный период
        training_conditions = [
            TrainingSession.user_id == user.id,
            TrainingSession.completed_at.isnot(None)
        ]
        
        if period_filter is not None:
            training_conditions.append(period_filter)
        
        total_sessions_query = select(func.count(TrainingSession.id)).where(*training_conditions)
        total_sessions_result = await session.execute(total_sessions_query)
        total_sessions = total_sessions_result.scalar()
        
        total_correct_query = select(func.sum(TrainingSession.words_correct)).where(*training_conditions)
        total_correct_result = await session.execute(total_correct_query)
        total_correct = total_correct_result.scalar() or 0
        
        total_words_trained_query = select(func.sum(TrainingSession.words_total)).where(*training_conditions)
        total_words_trained_result = await session.execute(total_words_trained_query)
        total_words_trained = total_words_trained_result.scalar() or 0
        
        # Статистика по словам, выученным за период
        learned_in_period = 0
        if period_filter is not None:
            learned_in_period_query = select(func.count(UserWord.id)).where(
                UserWord.user_id == user.id,
                UserWord.is_learned == True,
                UserWord.learned_at >= period_start
            )
            learned_in_period_result = await session.execute(learned_in_period_query)
            learned_in_period = learned_in_period_result.scalar()
        
        # Вычисляем процент точности
        accuracy = (total_correct / total_words_trained * 100) if total_words_trained > 0 else 0
        
        # Формируем сообщение со статистикой
        stats_text = f"📊 <b>Статистика обучения {period_name}</b>\n\n"
        
        if days is not None:
            stats_text += f"📅 Период: <b>{period_start.strftime('%d.%m.%Y')} - {datetime.utcnow().strftime('%d.%m.%Y')}</b>\n\n"
        
        # Словарь (текущее состояние)
        stats_text += f"📚 <b>Текущий словарь:</b>\n"
        stats_text += f"• Всего слов в изучении: <b>{total_words - learned_words}</b>\n"
        stats_text += f"• Выучено слов: <b>{learned_words}</b> ✅\n"
        stats_text += f"• Готово к повторению: <b>{ready_words}</b> 🔴\n\n"
        
        # Активность за период
        if days is not None:
            stats_text += f"🎯 <b>Активность {period_name}:</b>\n"
            if learned_in_period > 0:
                stats_text += f"• Выучено новых слов: <b>{learned_in_period}</b> 🎉\n"
        else:
            stats_text += f"🎯 <b>Тренировки {period_name}:</b>\n"
        
        stats_text += f"• Завершено тренировок: <b>{total_sessions}</b>\n"
        stats_text += f"• Всего слов изучено: <b>{total_words_trained}</b>\n"
        stats_text += f"• Правильных ответов: <b>{total_correct}</b>\n"
        
        if total_words_trained > 0:
            stats_text += f"• Точность ответов: <b>{accuracy:.1f}%</b>\n\n"
        else:
            stats_text += f"• Точность ответов: <b>--</b>\n\n"
            
        if days is None and learned_words > 0:
            progress = (learned_words / (total_words or 1)) * 100
            stats_text += f"🏆 <b>Общий прогресс: {progress:.1f}% от всех слов</b>\n\n"
        
        if days is None:
            stats_text += f"📅 Аккаунт создан: {user.created_at.strftime('%d.%m.%Y')}"
        
        return stats_text, period_name

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start - регистрация пользователя"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Проверяем, есть ли пользователь в БД
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        existing_user = user_result.scalar_one_or_none()
        
        if not existing_user:
            # Создаем нового пользователя
            new_user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            session.add(new_user)
            await session.commit()
            
            welcome_text = (
                f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
                f"🎯 <b>Я - бот для изучения словарных слов!</b>\n\n"
                f"<b>Что я умею:</b>\n"
                f"📝 Создавать тренировки с пропущенными буквами\n"
                f"📚 Ведение личного словаря ошибок\n"
                f"🔔 Напоминания по системе интервальных повторений\n"
                f"📊 Отслеживание прогресса обучения\n\n"
                f"<b>Как работает система:</b>\n"
                f"1. Проходите тренировки из 25 слов\n"
                f"2. Неправильные ответы попадают в ваш личный словарь\n"
                f"3. Получайте напоминания для повторения по кривой Эббингауза\n"
                f"4. Постепенно увеличивайте интервалы между повторениями\n\n"
                f"Нажмите \"🎯 Начать тренировку\" чтобы приступить к изучению!"
            )
        else:
            welcome_text = (
                f"👋 С возвращением, {message.from_user.first_name}!\n\n"
                f"Готовы продолжить изучение словарных слов? 📚\n"
                f"Нажмите \"🎯 Начать тренировку\" для продолжения обучения!"
            )
    
    # Создаем главную клавиатуру
    from main import get_main_keyboard
    keyboard = get_main_keyboard()
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(F.text == "📚 Мой словарь")
async def show_dictionary(message: Message):
    """Показывает личный словарь пользователя"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        # Получаем слова пользователя
        user_words_query = select(UserWord, Word).join(Word).where(
            UserWord.user_id == user.id
        ).order_by(UserWord.next_repetition)
        
        user_words_result = await session.execute(user_words_query)
        user_words = user_words_result.all()
        
        if not user_words:
            dictionary_text = (
                "📚 <b>Ваш личный словарь пуст!</b>\n\n"
                "Слова появятся здесь после первых ошибок в тренировках.\n"
                "Начните тренировку, чтобы пополнить словарь!"
            )
        else:
            dictionary_text = f"📚 <b>Ваш личный словарь</b>\n\n"
            
            for i, (user_word, word) in enumerate(user_words[:20], 1):
                # Определяем статус
                now = datetime.utcnow()
                if user_word.is_learned:
                    status = "✅ Выучено"
                elif user_word.next_repetition <= now:
                    status = "🔴 Готово к повторению"
                else:
                    time_left = user_word.next_repetition - now
                    if time_left.days > 0:
                        status = f"⏰ Через {time_left.days} дней"
                    elif time_left.seconds > 3600:
                        hours = time_left.seconds // 3600
                        status = f"⏰ Через {hours} часов"
                    else:
                        minutes = time_left.seconds // 60
                        status = f"⏰ Через {minutes} минут"
                
                dictionary_text += (
                    f"{i}. <b>{word.word}</b> (ошибок: {user_word.mistakes_count})\n"
                    f"   {status}\n\n"
                )
            
            if len(user_words) > 20:
                dictionary_text += f"... и еще {len(user_words) - 20} слов\n\n"
        
        # Добавляем кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")]
        ])
        
        await message.answer(dictionary_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показывает меню выбора периода для статистики обучения"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        # Показываем меню выбора периода
        stats_text = (
            "📊 <b>Статистика обучения</b>\n\n"
            "📈 Выберите период для просмотра статистики:\n\n"
            "📅 <b>Доступные периоды:</b>\n"
            "• 7 дней - активность за неделю\n"
            "• 14 дней - активность за две недели\n" 
            "• 21 день - активность за три недели\n"
            "• 30 дней - активность за месяц\n"
            "• Все время - полная статистика"
        )
        
        # Создаем клавиатуру выбора периода
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 7 дней", callback_data="stats_period_7"),
                InlineKeyboardButton(text="📅 14 дней", callback_data="stats_period_14")
            ],
            [
                InlineKeyboardButton(text="📅 21 день", callback_data="stats_period_21"),
                InlineKeyboardButton(text="📅 30 дней", callback_data="stats_period_30")
            ],
            [InlineKeyboardButton(text="📊 За все время", callback_data="stats_period_all")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
        
        await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Показывает настройки пользователя"""
    user_id = message.from_user.id
    
    async for session in get_session():
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        settings_text = f"⚙️ <b>Настройки</b>\n\n"
        settings_text += f"🔔 Уведомления: {'✅ Включены' if user.notifications_enabled else '❌ Отключены'}\n"
        settings_text += f"📱 Аккаунт: {'✅ Активен' if user.is_active else '❌ Неактивен'}\n\n"
        settings_text += f"<b>Время уведомлений:</b> 9:00, 14:00, 19:00\n"
        settings_text += f"<b>Система повторений:</b> Кривая Эббингауза"
        
        # Кнопки настроек
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔔 Отключить уведомления" if user.notifications_enabled else "🔔 Включить уведомления",
                callback_data="toggle_notifications"
            )],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ])
        
        await message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(F.text == "❓ Помощь")
async def show_help(message: Message):
    """Показывает справку по использованию бота"""
    help_text = (
        f"❓ <b>Справка по использованию бота</b>\n\n"
        f"<b>🎯 Тренировки:</b>\n"
        f"• Каждая тренировка содержит 25 слов\n"
        f"• Некоторые буквы в словах скрыты знаком '_'\n"
        f"• Введите пропущенные буквы\n"
        f"• Неправильные ответы добавляются в личный словарь\n\n"
        f"<b>📚 Личный словарь:</b>\n"
        f"• Содержит все слова, в которых вы ошиблись\n"
        f"• Показывает количество ошибок по каждому слову\n"
        f"• Указывает время следующего повторения\n\n"
        f"<b>🔔 Система напоминаний:</b>\n"
        f"• Основана на кривой забывания Эббингауза\n"
        f"• Интервалы: 20 мин → 1 час → 9 часов → 1 день → 2 дня → 6 дней → 31 день\n"
        f"• Напоминания приходят в 9:00, 14:00 и 19:00\n\n"
        f"<b>📊 Статистика:</b>\n"
        f"• Отслеживает ваш прогресс\n"
        f"• Показывает точность ответов\n"
        f"• Ведет учет выученных слов\n\n"
        f"<b>💡 Советы:</b>\n"
        f"• Регулярно проходите тренировки\n"
        f"• Не игнорируйте напоминания\n"
        f"• Повторяйте слова из личного словаря\n"
        f"• Стремитесь к 100% точности!"
    )
    
    await message.answer(help_text, parse_mode="HTML")

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Переключает уведомления пользователя"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        user.notifications_enabled = not user.notifications_enabled
        await session.commit()
        
        status = "включены" if user.notifications_enabled else "отключены"
        
        # Обновляем текст сообщения
        settings_text = f"⚙️ <b>Настройки</b>\n\n"
        settings_text += f"🔔 Уведомления: {'✅ Включены' if user.notifications_enabled else '❌ Отключены'}\n"
        settings_text += f"📱 Аккаунт: {'✅ Активен' if user.is_active else '❌ Неактивен'}\n\n"
        settings_text += f"<b>Время уведомлений:</b> 9:00, 14:00, 19:00\n"
        settings_text += f"<b>Система повторений:</b> Кривая Эббингауза"
        
        # Кнопки настроек
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔔 Отключить уведомления" if user.notifications_enabled else "🔔 Включить уведомления",
                callback_data="toggle_notifications"
            )],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ])
        
        await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer(f"🔔 Уведомления {status}")

@router.callback_query(F.data.in_(["my_dictionary", "statistics", "help"]))
async def handle_inline_callbacks(callback: CallbackQuery):
    """Обработчик inline кнопок"""
    if callback.data == "my_dictionary":
        await show_dictionary_callback(callback)
    elif callback.data == "statistics":
        await statistics_callback(callback)
    elif callback.data == "help":
        await show_help_callback(callback)
    
    await callback.answer()

async def show_dictionary_callback(callback: CallbackQuery):
    """Показывает личный словарь пользователя для колбэка"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        # Получаем слова пользователя
        user_words_query = select(UserWord, Word).join(Word).where(
            UserWord.user_id == user.id
        ).order_by(UserWord.next_repetition)
        
        user_words_result = await session.execute(user_words_query)
        user_words = user_words_result.all()
        
        if not user_words:
            dictionary_text = (
                "📚 <b>Ваш личный словарь пуст!</b>\n\n"
                "Слова появятся здесь после первых ошибок в тренировках.\n"
                "Начните тренировку, чтобы пополнить словарь!"
            )
        else:
            dictionary_text = f"📚 <b>Ваш личный словарь</b>\n\n"
            
            for i, (user_word, word) in enumerate(user_words[:20], 1):
                # Определяем статус
                now = datetime.utcnow()
                if user_word.is_learned:
                    status = "✅ Выучено"
                elif user_word.next_repetition <= now:
                    status = "🔴 Готово к повторению"
                else:
                    time_left = user_word.next_repetition - now
                    if time_left.days > 0:
                        status = f"⏰ Через {time_left.days} дней"
                    elif time_left.seconds > 3600:
                        hours = time_left.seconds // 3600
                        status = f"⏰ Через {hours} часов"
                    else:
                        minutes = time_left.seconds // 60
                        status = f"⏰ Через {minutes} минут"
                
                dictionary_text += (
                    f"{i}. <b>{word.word}</b> (ошибок: {user_word.mistakes_count})\n"
                    f"   {status}\n\n"
                )
            
            if len(user_words) > 20:
                dictionary_text += f"... и еще {len(user_words) - 20} слов\n\n"
        
        # Добавляем кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")]
        ])
        
        await callback.message.answer(dictionary_text, parse_mode="HTML", reply_markup=keyboard)



async def show_help_callback(callback: CallbackQuery):
    """Показывает справку по использованию бота для колбэка"""
    help_text = (
        f"❓ <b>Справка по использованию бота</b>\n\n"
        f"<b>🎯 Тренировки:</b>\n"
        f"• Каждая тренировка содержит 25 слов\n"
        f"• Некоторые буквы в словах скрыты знаком '_'\n"
        f"• Введите пропущенные буквы\n"
        f"• Неправильные ответы добавляются в личный словарь\n\n"
        f"<b>📚 Личный словарь:</b>\n"
        f"• Содержит все слова, в которых вы ошиблись\n"
        f"• Показывает количество ошибок по каждому слову\n"
        f"• Указывает время следующего повторения\n\n"
        f"<b>🔔 Система напоминаний:</b>\n"
        f"• Основана на кривой забывания Эббингауза\n"
        f"• Интервалы: 20 мин → 1 час → 9 часов → 1 день → 2 дня → 6 дней → 31 день\n"
        f"• Напоминания приходят в 9:00, 14:00 и 19:00\n\n"
        f"<b>📊 Статистика:</b>\n"
        f"• Отслеживает ваш прогресс\n"
        f"• Показывает точность ответов\n"
        f"• Ведет учет выученных слов\n\n"
        f"<b>💡 Советы:</b>\n"
        f"• Регулярно проходите тренировки\n"
        f"• Не игнорируйте напоминания\n"
        f"• Повторяйте слова из личного словаря\n"
        f"• Стремитесь к 100% точности!"
    )
    
    await callback.message.answer(help_text, parse_mode="HTML")

@router.message(Command("dictionary"))
async def cmd_dictionary(message: Message):
    """Команда /dictionary"""
    await show_dictionary(message)

@router.message(Command("statistics"))
async def cmd_statistics(message: Message):
    """Команда /statistics"""
    await show_statistics(message)

@router.callback_query(F.data.startswith("stats_period_"))
async def show_period_statistics(callback: CallbackQuery):
    """Показывает статистику за выбранный период"""
    user_id = callback.from_user.id
    period = callback.data.replace("stats_period_", "")
    
    # Определяем количество дней
    days_map = {
        "7": 7,
        "14": 14,
        "21": 21,
        "30": 30,
        "all": None
    }
    
    days = days_map.get(period)
    if days is None and period != "all":
        await callback.answer("❌ Неверный период")
        return
    
    # Генерируем статистику
    stats_text, period_name = await generate_user_statistics(user_id, days)
    
    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 7 дней", callback_data="stats_period_7"),
            InlineKeyboardButton(text="📅 14 дней", callback_data="stats_period_14")
        ],
        [
            InlineKeyboardButton(text="📅 21 день", callback_data="stats_period_21"),
            InlineKeyboardButton(text="📅 30 дней", callback_data="stats_period_30")
        ],
        [InlineKeyboardButton(text="📊 За все время", callback_data="stats_period_all")],
        [
            InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training"),
            InlineKeyboardButton(text="📚 Мой словарь", callback_data="my_dictionary")
        ],
        [InlineKeyboardButton(text="🔙 Назад к выбору", callback_data="back_to_stats_menu")]
    ])
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "back_to_stats_menu")
async def back_to_stats_menu(callback: CallbackQuery):
    """Возврат к меню выбора периода статистики"""
    stats_text = (
        "📊 <b>Статистика обучения</b>\n\n"
        "📈 Выберите период для просмотра статистики:\n\n"
        "📅 <b>Доступные периоды:</b>\n"
        "• 7 дней - активность за неделю\n"
        "• 14 дней - активность за две недели\n" 
        "• 21 день - активность за три недели\n"
        "• 30 дней - активность за месяц\n"
        "• Все время - полная статистика"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 7 дней", callback_data="stats_period_7"),
            InlineKeyboardButton(text="📅 14 дней", callback_data="stats_period_14")
        ],
        [
            InlineKeyboardButton(text="📅 21 день", callback_data="stats_period_21"),
            InlineKeyboardButton(text="📅 30 дней", callback_data="stats_period_30")
        ],
        [InlineKeyboardButton(text="📊 За все время", callback_data="stats_period_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")  
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    main_text = (
        "🎓 <b>Добро пожаловать в бот для изучения морфем!</b>\n\n"
        "🔍 Выберите действие:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать тренировку", callback_data="start_training")],
        [InlineKeyboardButton(text="📚 Мой словарь", callback_data="my_dictionary")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")]
    ])
    
    await callback.message.edit_text(main_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "statistics")
async def statistics_callback(callback: CallbackQuery):
    """Обработчик кнопки статистики"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден.")
            return
        
        # Показываем меню выбора периода
        stats_text = (
            "📊 <b>Статистика обучения</b>\n\n"
            "📈 Выберите период для просмотра статистики:\n\n"
            "📅 <b>Доступные периоды:</b>\n"
            "• 7 дней - активность за неделю\n"
            "• 14 дней - активность за две недели\n" 
            "• 21 день - активность за три недели\n"
            "• 30 дней - активность за месяц\n"
            "• Все время - полная статистика"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 7 дней", callback_data="stats_period_7"),
                InlineKeyboardButton(text="📅 14 дней", callback_data="stats_period_14")
            ],
            [
                InlineKeyboardButton(text="📅 21 день", callback_data="stats_period_21"),
                InlineKeyboardButton(text="📅 30 дней", callback_data="stats_period_30")
            ],
            [InlineKeyboardButton(text="📊 За все время", callback_data="stats_period_all")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings"""
    await show_settings(message)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    await show_help(message) 