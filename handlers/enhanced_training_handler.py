from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func

from database.database import get_session
from database.models import User, Word, TrainingSession, TrainingAnswer
from services.word_service import WordService
from services.support_phrases_service import support_phrases_service
from services.leveling_service import leveling_service
from typing import Dict, List
from aiogram.filters import Command
from config import MORPHEME_TYPES
from datetime import datetime

router = Router()

class TrainingStates(StatesGroup):
    choosing_morpheme_type = State()
    waiting_for_answer = State()
    waiting_for_spelling_choice = State()  # Добавляем новое состояние для выбора написания

# Словарь для хранения данных тренировки (в продакшене лучше использовать Redis)
training_data: Dict[int, Dict] = {}

@router.message(F.text == "🎯 Начать тренировку")
async def start_training(message: Message, state: FSMContext):
    """Начало тренировки - выбор типа морфемы"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        # Создаем клавиатуру выбора типа тренировки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Быстрая тренировка (25 слов)", callback_data="quick_training")],
            [InlineKeyboardButton(text="⚙️ Тонкая настройка", callback_data="custom_training")]
        ])
        
        await message.answer(
            "🎯 <b>Выбор типа тренировки</b>\n\n"
            "⚡ <b>Быстрая тренировка</b> - смешанная тренировка на 25 слов\n"
            "⚙️ <b>Тонкая настройка</b> - выбор количества слов, типа морфем и режима\n\n"
            "Что предпочитаете?",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.set_state(TrainingStates.choosing_morpheme_type)

@router.callback_query(F.data == "quick_training")
async def process_quick_training(callback: CallbackQuery, state: FSMContext):
    """Запускает быструю тренировку (25 слов, смешанная)"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден.")
            return
        
        # Получаем слова для смешанной тренировки (25 слов)
        words = await WordService.get_training_words(session, user.id, 25)
        training_type_name = "Быстрая тренировка (смешанная)"
        
        if not words:
            await callback.message.edit_text(
                "📚 Нет доступных слов для тренировки.\n"
                "Попросите администратора добавить слова.",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Создаем сессию тренировки
        training_session = TrainingSession(
            user_id=user.id,
            session_type='quick_training_mixed',
            words_total=len(words)
        )
        session.add(training_session)
        await session.commit()
        await session.refresh(training_session)
        
        # Подготавливаем данные тренировки
        training_data[user_id] = {
            'words': words,
            'current_word_index': 0,
            'correct_answers': 0,
            'incorrect_words': [],
            'answers': [],
            'training_type_name': training_type_name,
            'session_id': training_session.id
        }
        
        await send_next_word_callback(callback, user_id, state)

@router.callback_query(F.data == "custom_training")
async def process_custom_training(callback: CallbackQuery, state: FSMContext):
    """Переходит к тонкой настройке тренировки"""
    # Создаем клавиатуру выбора количества слов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Быстрая (10 слов)", callback_data="word_count_10")],
        [InlineKeyboardButton(text="📚 Стандартная (25 слов)", callback_data="word_count_25")],
        [InlineKeyboardButton(text="🔥 Колоссальная (50 слов)", callback_data="word_count_50")]
    ])
    
    await callback.message.edit_text(
        "⚙️ <b>Тонкая настройка - Выбор количества слов</b>\n\n"
        "⚡ <b>Быстрая (10 слов)</b> - для занятых людей\n"
        "📚 <b>Стандартная (25 слов)</b> - оптимальная нагрузка\n"
        "🔥 <b>Колоссальная (50 слов)</b> - для суперактивных\n\n"
        "Выберите подходящий размер:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("word_count_"))
async def process_word_count_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества слов"""
    word_count = int(callback.data.replace("word_count_", ""))
    
    # Сохраняем выбранное количество слов в состояние
    await state.update_data(word_count=word_count)
    
    # Показываем выбор типа тренировки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌿 {MORPHEME_TYPES['roots']}", callback_data="training_roots")],
        [InlineKeyboardButton(text=f"🔤 {MORPHEME_TYPES['prefixes']}", callback_data="training_prefixes")],
        [InlineKeyboardButton(text=f"🔚 {MORPHEME_TYPES['endings']}", callback_data="training_endings")],
        [InlineKeyboardButton(text=f"✍️ {MORPHEME_TYPES['spelling']}", callback_data="training_spelling")],
        [InlineKeyboardButton(text=f"📝 {MORPHEME_TYPES['n_nn']}", callback_data="training_n_nn")],
        [InlineKeyboardButton(text=f"🔤 {MORPHEME_TYPES['suffix']}", callback_data="training_suffix")],
        [InlineKeyboardButton(text=f"🎵 {MORPHEME_TYPES['stress']}", callback_data="training_stress")],
        [InlineKeyboardButton(text=f"🚫 {MORPHEME_TYPES['ne_particle']}", callback_data="training_ne_particle")],
        [InlineKeyboardButton(text="🌈 Смешанная тренировка", callback_data="training_mixed")]
    ])
    
    count_text = {10: "⚡ Быстрая", 25: "📚 Стандартная", 50: "🔥 Колоссальная"}
    
    await callback.message.edit_text(
        f"✅ Выбрано: {count_text.get(word_count, str(word_count))} ({word_count} слов)\n\n"
        f"🎯 <b>Выбор типа тренировки</b>\n\n"
        f"Выберите тип слов для тренировки или смешанную тренировку:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("training_"))
async def process_morpheme_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа морфемы"""
    morpheme_type = callback.data.replace("training_", "")
    user_id = callback.from_user.id
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден.")
            return
        
        # Получаем выбранное количество слов из состояния
        user_data = await state.get_data()
        word_count = user_data.get('word_count', 25)  # по умолчанию 25
        
        # Получаем слова для тренировки в зависимости от выбранного типа
        if morpheme_type == "mixed":
            words = await WordService.get_training_words(session, user.id, word_count)
            training_type_name = "Смешанная тренировка"
        else:
            words = await WordService.get_training_words_by_morpheme(session, user.id, morpheme_type, word_count)
            training_type_name = MORPHEME_TYPES.get(morpheme_type, "Неизвестный тип")
        
        if not words:
            await callback.message.edit_text(
                f"📚 Нет доступных слов для тренировки типа '{training_type_name}'.\n"
                f"Попросите администратора добавить слова этого типа.",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Создаем сессию тренировки
        training_session = TrainingSession(
            user_id=user.id,
            session_type=f'training_{morpheme_type}',
            words_total=len(words)
        )
        session.add(training_session)
        await session.commit()
        await session.refresh(training_session)
        
        # Подготавливаем данные тренировки
        training_data[user_id] = {
            'session_id': training_session.id,
            'words': words,
            'current_word_index': 0,
            'correct_answers': 0,
            'incorrect_words': [],
            'answers': [],
            'morpheme_type': morpheme_type,
            'training_type_name': training_type_name
        }
        
        await send_next_word_callback(callback, user_id, state)

@router.callback_query(F.data.startswith("spelling_answer_"))
async def process_spelling_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора варианта написания"""
    callback_parts = callback.data.split("_", 4)  # spelling_answer_{user_id}_{option_index}_{option_text}
    if len(callback_parts) < 5:
        await callback.answer("❌ Ошибка в данных")
        return
        
    user_id = int(callback_parts[2])
    chosen_option = "_".join(callback_parts[4:])  # Восстанавливаем полный текст варианта
    
    if user_id not in training_data:
        await callback.message.edit_text("❌ Тренировка не найдена. Начните новую тренировку.")
        return
    
    data = training_data[user_id]
    correct_answer = data['current_correct_answer']
    current_word = data['current_word']
    
    # Проверяем правильность ответа
    if current_word.morpheme_type == 'stress':
        # Для ударений сравниваем точно (с учетом ударений)
        is_correct = chosen_option.strip() == correct_answer.strip()
    else:
        # Для остальных типов - как раньше
        is_correct = chosen_option.strip().lower() == correct_answer.strip().lower()
    
    # Сохраняем ответ
    answer_data = {
        'word': current_word,
        'user_answer': chosen_option,
        'correct_answer': correct_answer,
        'is_correct': is_correct
    }
    data['answers'].append(answer_data)
    
    if is_correct:
        data['correct_answers'] += 1
        result_text = f"✅ <b>Правильно!</b>\n\n" \
                     f"Ответ: <b>{chosen_option}</b>"
    else:
        data['incorrect_words'].append(current_word)
        result_text = f"❌ <b>Неправильно!</b>\n\n" \
                     f"Ваш ответ: <b>{chosen_option}</b>\n" \
                     f"Правильный ответ: <b>{correct_answer}</b>"
    
    # Переходим к следующему слову
    data['current_word_index'] += 1
    
    # Показываем результат без кнопки и сразу переходим к следующему слову
    await callback.message.edit_text(result_text, parse_mode="HTML")
    await callback.answer()
    
    # Автоматически переходим к следующему слову
    await send_next_word_callback(callback, user_id, state)



async def send_next_word_callback(callback: CallbackQuery, user_id: int, state: FSMContext):
    """Отправляет следующее слово для тренировки (версия для callback)"""
    if user_id not in training_data:
        await callback.message.edit_text("❌ Тренировка не найдена. Начните новую тренировку.")
        return
    
    data = training_data[user_id]
    current_index = data['current_word_index']
    
    if current_index >= len(data['words']):
        await finish_training_callback(callback, user_id)
        return
    
    word = data['words'][current_index]
    puzzle, correct_answer = WordService.create_word_puzzle(word)
    
    # Сохраняем правильный ответ для текущего слова
    data['current_correct_answer'] = correct_answer
    data['current_word'] = word
    
    # Формируем текст задания
    question_text = (
        f"🎯 <b>{data['training_type_name']}</b>\n\n"
        f"📝 <b>Слово {current_index + 1} из {len(data['words'])}</b>\n\n"
    )
    
    # Добавляем определение
    if word.definition:
        question_text += f"📖 <b>Определение:</b> {word.definition}\n\n"
    
    # Формируем puzzle с пояснением в скобках, если есть
    if word.explanation:
        puzzle_with_explanation = f"{puzzle} (<u>{word.explanation}</u>)"
    else:
        puzzle_with_explanation = puzzle
    
    # Проверяем тип морфемы для разного интерфейса
    if word.morpheme_type in ['spelling', 'stress', 'ne_particle']:
        # Для типов с выбором вариантов
        type_icons = {
            'spelling': '✍️',
            'stress': '🔤',
            'ne_particle': '🚫'
        }
        type_labels = {
            'spelling': 'Как правильно?',
            'stress': 'Как правильно?',
            'ne_particle': 'Как правильно?'
        }
        
        icon = type_icons.get(word.morpheme_type, '✍️')
        label = type_labels.get(word.morpheme_type, 'Как правильно?')
        
        question_text += (
            f"{icon} <b>{label}</b>\n"
            f"<code>{puzzle_with_explanation}</code>\n\n"
        )
        
        # Создаем варианты ответов
        options = WordService.create_options_for_word(word)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for i, option in enumerate(options):
            button = InlineKeyboardButton(
                text=option, 
                callback_data=f"spelling_answer_{user_id}_{i}_{option}"
            )
            keyboard.inline_keyboard.append([button])
        
        # Добавляем кнопку завершения тренировки
        finish_button = InlineKeyboardButton(
            text="🚪 Завершить тренировку", 
            callback_data="finish_training_request"
        )
        keyboard.inline_keyboard.append([finish_button])
        
        await callback.message.edit_text(question_text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(TrainingStates.waiting_for_spelling_choice)
        
    else:
        # Для типов с вводом букв (roots, prefixes, endings, n_nn, suffix)
        question_text += f"<code>{puzzle_with_explanation}</code>"
        
        # Добавляем кнопку завершения тренировки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Завершить тренировку", callback_data="finish_training_request")]
        ])
        
        await callback.message.edit_text(question_text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(TrainingStates.waiting_for_answer)
    
    await callback.answer()

async def send_next_word(message: Message, user_id: int, state: FSMContext):
    """Отправляет следующее слово для тренировки"""
    if user_id not in training_data:
        await message.answer("❌ Тренировка не найдена. Начните новую тренировку.")
        return
    
    data = training_data[user_id]
    current_index = data['current_word_index']
    
    if current_index >= len(data['words']):
        await finish_training(message, user_id)
        return
    
    word = data['words'][current_index]
    puzzle, correct_answer = WordService.create_word_puzzle(word)
    
    # Сохраняем правильный ответ для текущего слова
    data['current_correct_answer'] = correct_answer
    data['current_word'] = word
    
    # Формируем текст задания
    question_text = (
        f"🎯 <b>{data['training_type_name']}</b>\n\n"
        f"📝 <b>Слово {current_index + 1} из {len(data['words'])}</b>\n\n"
    )
    
    # Добавляем определение
    if word.definition:
        question_text += f"📖 <b>Определение:</b> {word.definition}\n\n"
    
    # Формируем puzzle с пояснением в скобках, если есть
    if word.explanation:
        puzzle_with_explanation = f"{puzzle} (<u>{word.explanation}</u>)"
    else:
        puzzle_with_explanation = puzzle
    
    # Проверяем тип морфемы для разного интерфейса
    if word.morpheme_type in ['spelling', 'stress', 'ne_particle']:
        # Для типов с выбором вариантов
        type_icons = {
            'spelling': '✍️',
            'stress': '🔤',
            'ne_particle': '🚫'
        }
        type_labels = {
            'spelling': 'Как правильно?',
            'stress': 'Как правильно?',
            'ne_particle': 'Как правильно?'
        }
        
        icon = type_icons.get(word.morpheme_type, '✍️')
        label = type_labels.get(word.morpheme_type, 'Как правильно?')
        
        question_text += (
            f"{icon} <b>{label}</b>\n"
            f"<code>{puzzle_with_explanation}</code>\n\n"
        )
        
        # Создаем варианты ответов
        options = WordService.create_options_for_word(word)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for i, option in enumerate(options):
            button = InlineKeyboardButton(
                text=option, 
                callback_data=f"spelling_answer_{user_id}_{i}_{option}"
            )
            keyboard.inline_keyboard.append([button])
        
        # Добавляем кнопку завершения тренировки
        finish_button = InlineKeyboardButton(
            text="🚪 Завершить тренировку", 
            callback_data="finish_training_request"
        )
        keyboard.inline_keyboard.append([finish_button])
        
        await message.answer(question_text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(TrainingStates.waiting_for_spelling_choice)
        
    else:
        # Для типов с вводом букв (roots, prefixes, endings, n_nn, suffix)
        question_text += f"<code>{puzzle_with_explanation}</code>"
        
        # Добавляем кнопку завершения тренировки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Завершить тренировку", callback_data="finish_training_request")]
        ])
        
        await message.answer(question_text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(TrainingStates.waiting_for_answer)

@router.message(TrainingStates.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext):
    """Обработка ответа пользователя"""
    user_id = message.from_user.id
    
    if user_id not in training_data:
        await message.answer("❌ Тренировка не найдена. Начните новую тренировку.")
        await state.clear()
        return
    
    data = training_data[user_id]
    user_answer = message.text.strip()
    correct_answer = data['current_correct_answer']
    current_word = data['current_word']
    
    is_correct = WordService.check_answer("", user_answer, correct_answer)
    
    # Сохраняем ответ
    answer_data = {
        'word': current_word,
        'user_answer': user_answer,
        'correct_answer': correct_answer,
        'is_correct': is_correct
    }
    data['answers'].append(answer_data)
    
    if is_correct:
        data['correct_answers'] += 1
        
        # Начисляем опыт за правильный ответ
        async for session in get_session():
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if user:
                # Рассчитываем награду опыта
                difficulty = getattr(current_word, 'difficulty_level', 1)
                streak = data['correct_answers'] - 1  # Текущая серия правильных ответов
                experience_reward = leveling_service.calculate_experience_reward(difficulty, streak)
                
                # Добавляем опыт и проверяем повышение уровня
                level_up, new_level = await leveling_service.add_experience(session, user, experience_reward)
                
                # Уведомление о повышении уровня
                if level_up:
                    level_name = leveling_service.get_level_name(new_level)
                    await message.answer(
                        f"🎉 <b>Поздравляем!</b>\n\n"
                        f"🆙 Вы достигли нового уровня!\n"
                        f"🏆 <b>Уровень {new_level}:</b> {level_name}\n"
                        f"⭐ +{experience_reward} опыта",
                        parse_mode="HTML"
                    )
    else:
        data['incorrect_words'].append(current_word)
        await message.answer(f"❌ Неправильно. Правильный ответ: <b>{correct_answer}</b>", parse_mode="HTML")
    
    # Переходим к следующему слову
    data['current_word_index'] += 1
    
    # Проверяем, нужно ли показать поддерживающую фразу (каждые 3 слова и только после правильного ответа)
    if is_correct and support_phrases_service.should_show_support_phrase(data['current_word_index']):
        support_message = support_phrases_service.get_support_message()
        await message.answer(support_message)
    
    await send_next_word(message, user_id, state)

async def finish_training(message: Message, user_id: int):
    """Завершение тренировки и показ результатов"""
    if user_id not in training_data:
        return
    
    data = training_data[user_id]
    
    async for session in get_session():
        # Обновляем сессию тренировки
        session_query = select(TrainingSession).where(TrainingSession.id == data['session_id'])
        training_session_result = await session.execute(session_query)
        training_session = training_session_result.scalar_one()
        
        training_session.words_correct = data['correct_answers']
        training_session.words_incorrect = len(data['incorrect_words'])
        training_session.completed_at = datetime.utcnow()
        
        # Сохраняем все ответы и обновляем прогресс каждого слова
        for answer_data in data['answers']:
            training_answer = TrainingAnswer(
                session_id=training_session.id,
                word_id=answer_data['word'].id,
                user_answer=answer_data['user_answer'],
                is_correct=answer_data['is_correct']
            )
            session.add(training_answer)
            
            # Обновляем прогресс слова (счетчик правильных ответов и интервалы)
            await WordService.update_word_progress(
                session, 
                training_session.user_id, 
                answer_data['word'].id, 
                answer_data['is_correct']
            )
        
        # Добавляем неправильные слова в личный словарь
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        for incorrect_word in data['incorrect_words']:
            await WordService.add_word_to_user_dictionary(session, user.id, incorrect_word.id)
        
        await session.commit()
    
    # Формируем результат тренировки
    accuracy = (data['correct_answers'] / len(data['words'])) * 100
    
    result_text = (
        f"🎉 <b>Тренировка '{data['training_type_name']}' завершена!</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"✅ Правильно: <b>{data['correct_answers']}</b> из <b>{len(data['words'])}</b>\n"
        f"📈 Точность: <b>{accuracy:.1f}%</b>\n\n"
    )
    
    if data['incorrect_words']:
        result_text += f"📚 <b>Слова добавлены в личный словарь:</b>\n"
        for word in data['incorrect_words']:
            result_text += f"• {word.word}\n"
        result_text += f"\n🔔 Эти слова появятся в следующих повторениях по системе интервальных повторений."
        
        # Предлагаем тренировку на ошибках только для обычных тренировок
        if data.get('training_mode', 'new') not in ['learned', 'error']:
            result_text += f"\n\n💪 <b>Хотите потренироваться на ошибках?</b>\n"
            result_text += f"Дополнительная тренировка поможет закрепить проблемные слова."
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔥 Да, потренироваться на ошибках", callback_data="start_error_training")],
                [InlineKeyboardButton(text="🏁 Нет, завершить", callback_data="decline_error_training")]
            ])
            
            await message.answer(result_text, parse_mode="HTML", reply_markup=keyboard)
            # НЕ очищаем данные тренировки - они нужны для тренировки на ошибках
            return
    else:
        result_text += f"🏆 <b>Отличная работа! Все ответы правильные!</b>"
    
    # Если нет ошибок или это тренировка на ошибках - показываем обычное завершение
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Новая тренировка", callback_data="start_training_new")],
        [InlineKeyboardButton(text="📚 Мой словарь", callback_data="my_dictionary")]
    ])
    
    await message.answer(result_text, parse_mode="HTML", reply_markup=keyboard)
    
    # Очищаем данные тренировки
    del training_data[user_id]

async def finish_training_callback(callback: CallbackQuery, user_id: int):
    """Завершение тренировки и показ результатов (версия для callback)"""
    if user_id not in training_data:
        return
    
    data = training_data[user_id]
    
    async for session in get_session():
        # Обновляем сессию тренировки
        session_query = select(TrainingSession).where(TrainingSession.id == data['session_id'])
        training_session_result = await session.execute(session_query)
        training_session = training_session_result.scalar_one()
        
        training_session.words_correct = data['correct_answers']
        training_session.words_incorrect = len(data['incorrect_words'])
        training_session.completed_at = datetime.utcnow()
        
        # Сохраняем все ответы
        for answer_data in data['answers']:
            training_answer = TrainingAnswer(
                session_id=training_session.id,
                word_id=answer_data['word'].id,
                user_answer=answer_data['user_answer'],
                is_correct=answer_data['is_correct']
            )
            session.add(training_answer)
        
        # Добавляем неправильные слова в личный словарь
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        for incorrect_word in data['incorrect_words']:
            await WordService.add_word_to_user_dictionary(session, user.id, incorrect_word.id)
        
        await session.commit()
    
    # Формируем результат тренировки
    accuracy = (data['correct_answers'] / len(data['words'])) * 100
    
    result_text = (
        f"🎉 <b>Тренировка '{data['training_type_name']}' завершена!</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"✅ Правильно: <b>{data['correct_answers']}</b> из <b>{len(data['words'])}</b>\n"
        f"📈 Точность: <b>{accuracy:.1f}%</b>\n\n"
    )
    
    if data['incorrect_words']:
        result_text += f"📚 <b>Слова добавлены в личный словарь:</b>\n"
        for word in data['incorrect_words']:
            result_text += f"• {word.word}\n"
        result_text += f"\n🔔 Эти слова появятся в следующих повторениях по системе интервальных повторений."
        
        # Предлагаем тренировку на ошибках только для обычных тренировок
        if data.get('training_mode', 'new') not in ['learned', 'error']:
            result_text += f"\n\n💪 <b>Хотите потренироваться на ошибках?</b>\n"
            result_text += f"Дополнительная тренировка поможет закрепить проблемные слова."
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔥 Да, потренироваться на ошибках", callback_data="start_error_training")],
                [InlineKeyboardButton(text="🏁 Нет, завершить", callback_data="decline_error_training")]
            ])
            
            await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=keyboard)
            # НЕ очищаем данные тренировки - они нужны для тренировки на ошибках
            return
        
    else:
        result_text += f"🏆 <b>Отличная работа! Все ответы правильные!</b>"
    
    # Если нет ошибок или это тренировка на ошибках - показываем обычное завершение
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Новая тренировка", callback_data="start_training_new")],
        [InlineKeyboardButton(text="📚 Мой словарь", callback_data="my_dictionary")]
    ])
    
    await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=keyboard)
    
    # Очищаем данные тренировки
    del training_data[user_id]

@router.callback_query(F.data == "start_training_new")
async def start_training_new(callback: CallbackQuery, state: FSMContext):
    """Начало новой тренировки"""
    user_id = callback.from_user.id
    
    # Создаем клавиатуру выбора типа морфемы
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌿 {MORPHEME_TYPES['roots']}", callback_data="training_roots")],
        [InlineKeyboardButton(text=f"🔤 {MORPHEME_TYPES['prefixes']}", callback_data="training_prefixes")],
        [InlineKeyboardButton(text=f"🔚 {MORPHEME_TYPES['endings']}", callback_data="training_endings")],
        [InlineKeyboardButton(text=f"✍️ {MORPHEME_TYPES['spelling']}", callback_data="training_spelling")],
        [InlineKeyboardButton(text="🎲 Смешанная тренировка", callback_data="training_mixed")]
    ])
    
    await callback.message.edit_text(
        "🎯 <b>Выбор типа тренировки</b>\n\n"
        "Выберите, какой тип морфемы вы хотите изучать:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await state.set_state(TrainingStates.choosing_morpheme_type)
    await callback.answer()

@router.callback_query(F.data == "finish_training_request")
async def request_finish_training(callback: CallbackQuery, state: FSMContext):
    """Запрос на досрочное завершение тренировки с подтверждением"""
    user_id = callback.from_user.id
    
    if user_id not in training_data:
        await callback.message.edit_text("❌ Тренировка не найдена. Начните новую тренировку.")
        await callback.answer()
        return
    
    data = training_data[user_id]
    current_index = data['current_word_index']
    total_words = len(data['words'])
    
    confirmation_text = (
        f"⚠️ <b>Досрочное завершение тренировки</b>\n\n"
        f"📊 Пройдено: <b>{current_index}</b> из <b>{total_words}</b> слов\n"
        f"✅ Правильно: <b>{data['correct_answers']}</b>\n\n"
        f"Вы уверены, что хотите завершить тренировку сейчас?\n"
        f"Прогресс будет сохранен."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Продолжить", callback_data="continue_training"),
            InlineKeyboardButton(text="🏁 Завершить", callback_data="confirm_finish_training")
        ]
    ])
    
    await callback.message.edit_text(confirmation_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "continue_training")
async def continue_training(callback: CallbackQuery, state: FSMContext):
    """Продолжение тренировки после отмены завершения"""
    user_id = callback.from_user.id
    await send_next_word_callback(callback, user_id, state)

@router.callback_query(F.data == "confirm_finish_training")
async def confirm_finish_training(callback: CallbackQuery, state: FSMContext):
    """Подтвержденное досрочное завершение тренировки"""
    user_id = callback.from_user.id
    await finish_training_callback(callback, user_id)

@router.callback_query(F.data == "start_error_training")
async def start_error_training(callback: CallbackQuery, state: FSMContext):
    """Запуск тренировки на ошибках"""
    user_id = callback.from_user.id
    
    if user_id not in training_data:
        await callback.message.edit_text("❌ Данные тренировки не найдены.")
        await callback.answer()
        return
    
    data = training_data[user_id]
    incorrect_words = data['incorrect_words']
    
    if not incorrect_words:
        await callback.message.edit_text("❌ Нет слов для тренировки на ошибках.")
        await callback.answer()
        return
    
    async for session in get_session():
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден.")
            return
        
        # Создаем новую сессию тренировки для ошибок
        error_training_session = TrainingSession(
            user_id=user.id,
            session_type='error_training',
            words_total=len(incorrect_words)
        )
        session.add(error_training_session)
        await session.commit()
        await session.refresh(error_training_session)
        
        # Подготавливаем данные тренировки на ошибках
        training_data[user_id] = {
            'session_id': error_training_session.id,
            'words': incorrect_words,
            'current_word_index': 0,
            'correct_answers': 0,
            'incorrect_words': [],
            'answers': [],
            'morpheme_type': 'error_training',
            'training_type_name': 'Тренировка на ошибках',
            'training_mode': 'error'
        }
        
        await send_next_word_callback(callback, user_id, state)

@router.callback_query(F.data == "decline_error_training")
async def decline_error_training(callback: CallbackQuery, state: FSMContext):
    """Отказ от тренировки на ошибках"""
    user_id = callback.from_user.id
    
    # Показываем обычное завершение тренировки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Новая тренировка", callback_data="start_training_new")],
        [InlineKeyboardButton(text="📚 Мой словарь", callback_data="my_dictionary")]
    ])
    
    await callback.message.edit_text(
        "🎉 <b>Тренировка завершена!</b>\n\n"
        "💡 Вы можете вернуться к изучению новых слов или повторить материал в любое время.",
        parse_mode="HTML", 
        reply_markup=keyboard
    )
    
    # Очищаем данные тренировки
    if user_id in training_data:
        del training_data[user_id]
    
    await callback.answer()

@router.message(Command("training"))
async def cmd_training(message: Message, state: FSMContext):
    """Команда для начала тренировки"""
    await start_training(message, state) 