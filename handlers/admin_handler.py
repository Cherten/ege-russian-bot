from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, delete
from database.database import get_session
from database.models import Word, User, UserWord, TrainingSession
from services.word_service import WordService
from config import ADMIN_ID, MORPHEME_TYPES

router = Router()

class AdminStates(StatesGroup):
    waiting_for_word = State()
    waiting_for_morpheme_type = State()
    waiting_for_explanation = State()
    waiting_for_pattern = State()
    waiting_for_hidden_letters = State()
    waiting_for_word_to_delete = State()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return str(user_id) == ADMIN_ID

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель управления ботом"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    async for session in get_session():
        # Статистика
        total_words_query = select(func.count(Word.id))
        total_words_result = await session.execute(total_words_query)
        total_words = total_words_result.scalar()
        
        total_users_query = select(func.count(User.id))
        total_users_result = await session.execute(total_users_query)
        total_users = total_users_result.scalar()
        
        admin_text = (
            f"👨‍💼 <b>Админ-панель</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"📚 Всего слов: {total_words}\n"
            f"👥 Всего пользователей: {total_users}\n\n"
            f"<b>Доступные команды:</b>\n"
            f"/add_word - Добавить новое слово\n"
            f"/list_words - Список всех слов\n"
            f"/delete_word - Удалить слово\n"
            f"/word_stats - Подробная статистика слов\n"
            f"/user_stats - Статистика пользователей"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить слово", callback_data="admin_add_word")],
            [InlineKeyboardButton(text="📋 Список слов", callback_data="admin_list_words")],
            [InlineKeyboardButton(text="🗑️ Удалить слово", callback_data="admin_delete_word")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
        ])
        
        await message.answer(admin_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(Command("add_word"))
async def start_add_word(message: Message, state: FSMContext):
    """Начало процесса добавления слова"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    await message.answer(
        "📝 <b>Добавление нового слова</b>\n\n"
        "Введите слово (только буквы):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_word)

@router.message(AdminStates.waiting_for_word)
async def process_word(message: Message, state: FSMContext):
    """Обработка введенного слова"""
    word = message.text.strip()  # НЕ применяем .lower() чтобы сохранить ударения!
    
    # Проверяем корректность слова (разрешаем буквы, дефисы и пробелы для слов написания)
    import re
    if not re.match(r'^[а-яёА-ЯЁa-zA-Z\-\s]+$', word) or len(word) < 2:
        await message.answer("❌ Слово должно содержать только буквы, дефисы или пробелы и быть длиной минимум 2 символа.")
        return
    
    # Проверяем, что слово еще не существует
    async for session in get_session():
        existing_query = select(Word).where(Word.word == word)
        existing_result = await session.execute(existing_query)
        existing_word = existing_result.scalar_one_or_none()
        
        if existing_word:
            await message.answer(f"❌ Слово '{word}' уже существует в базе данных.")
            return
    
    await state.update_data(word=word)
    
    # Создаем клавиатуру выбора типа морфемы сразу после ввода слова
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌿 {MORPHEME_TYPES['roots']}", callback_data="morpheme_roots")],
        [InlineKeyboardButton(text=f"🔤 {MORPHEME_TYPES['prefixes']}", callback_data="morpheme_prefixes")],
        [InlineKeyboardButton(text=f"🔚 {MORPHEME_TYPES['endings']}", callback_data="morpheme_endings")],
        [InlineKeyboardButton(text=f"✍️ {MORPHEME_TYPES['spelling']}", callback_data="morpheme_spelling")],
        [InlineKeyboardButton(text=f"📝 {MORPHEME_TYPES['n_nn']}", callback_data="morpheme_n_nn")],
        [InlineKeyboardButton(text=f"🔧 {MORPHEME_TYPES['suffix']}", callback_data="morpheme_suffix")],
        [InlineKeyboardButton(text=f"🎵 {MORPHEME_TYPES['stress']}", callback_data="morpheme_stress")],
        [InlineKeyboardButton(text=f"🚫 {MORPHEME_TYPES['ne_particle']}", callback_data="morpheme_ne_particle")]
    ])
    
    await message.answer(
        f"✅ Слово: <b>{word}</b>\n\n"
        f"Выберите тип морфемы для изучения:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(AdminStates.waiting_for_morpheme_type)

@router.callback_query(F.data.startswith("morpheme_"))
async def process_morpheme_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа морфемы"""
    morpheme_type = callback.data.replace("morpheme_", "")
    
    if morpheme_type not in MORPHEME_TYPES:
        await callback.answer("❌ Неверный тип морфемы")
        return
    
    await state.update_data(morpheme_type=morpheme_type)
    data = await state.get_data()
    
    # Создаем клавиатуру для выбора пояснения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Добавить пояснение", callback_data="add_explanation")],
        [InlineKeyboardButton(text="➡️ Пропустить пояснение", callback_data="skip_explanation")]
    ])
    
    await callback.message.edit_text(
        f"✅ Слово: <b>{data['word']}</b>\n"
        f"✅ Тип морфемы: <b>{MORPHEME_TYPES[morpheme_type]}</b>\n\n"
        f"Нужно ли добавить пояснение?\n"
        f"(Пояснения помогают различать слова типа 'компания - кампания')",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "add_explanation")
async def request_explanation(callback: CallbackQuery, state: FSMContext):
    """Запрос пояснения к слову"""
    await callback.message.edit_text(
        "📝 Введите пояснение к слову:\n\n"
        "<i>Пример: 'Компания (группа людей) - кампания (мероприятие)'</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_explanation)
    await callback.answer()

@router.callback_query(F.data == "skip_explanation")
async def skip_explanation(callback: CallbackQuery, state: FSMContext):
    """Пропуск пояснения"""
    await state.update_data(explanation="")
    await continue_to_pattern(callback.message, state)
    await callback.answer()

@router.message(AdminStates.waiting_for_explanation)
async def process_explanation(message: Message, state: FSMContext):
    """Обработка пояснения к слову"""
    explanation = message.text.strip()
    
    if len(explanation) < 3:
        await message.answer("❌ Пояснение должно содержать минимум 3 символа.")
        return
    
    await state.update_data(explanation=explanation)
    await continue_to_pattern(message, state)

async def continue_to_pattern(message: Message, state: FSMContext):
    """Переход к созданию шаблона"""
    data = await state.get_data()
    word = data['word']
    
    example_pattern = word[:2] + '_' * (len(word)-4) + word[-2:] if len(word) > 4 else word[0] + '_' * (len(word)-2) + word[-1]
    
    summary_text = (
        f"✅ Слово: <b>{word}</b>\n"
        f"✅ Тип морфемы: <b>{MORPHEME_TYPES[data['morpheme_type']]}</b>\n"
    )
    
    if data.get('explanation'):
        summary_text += f"✅ Пояснение: <b>{data['explanation']}</b>\n"
    
    summary_text += (
        f"\nТеперь введите шаблон с пропусками.\n"
        f"Используйте подчеркивание '_' для пропусков.\n\n"
        f"<b>Пример:</b> для слова '{word}' можно написать '{example_pattern}'\n"
        f"Введите ваш шаблон:"
    )
    
    await message.answer(summary_text, parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_pattern)

@router.message(AdminStates.waiting_for_pattern)
async def process_pattern(message: Message, state: FSMContext):
    """Обработка шаблона пропусков"""
    pattern = message.text.strip()  # НЕ применяем .lower() для сохранения ударений!
    data = await state.get_data()
    word = data['word']
    
    # Проверка длины шаблона убрана - админ всегда вводит правильно
    
    # Проверяем наличие пропусков (для типов с выбором вариантов проверяем скобки вместо подчеркиваний)
    morpheme_type = data.get('morpheme_type', '')
    if morpheme_type == 'spelling':
        if '(' not in pattern or ')' not in pattern:
            await message.answer("❌ Для слов написания шаблон должен содержать скобки вокруг спорной части. Например: (по)хорошему")
            return
    elif morpheme_type == 'stress':
        if '(' not in pattern or ')' not in pattern:
            await message.answer("❌ Для слов с ударениями шаблон должен содержать скобки вокруг возможных ударных букв. Например: крас(И)в(Е)е")
            return
    elif morpheme_type == 'ne_particle':
        if '(' not in pattern or ')' not in pattern:
            await message.answer("❌ Для слов с частицей НЕ шаблон должен содержать скобки. Например: (не)красивый")
            return
    else:
        if '_' not in pattern:
            await message.answer("❌ В шаблоне должен быть хотя бы один пропуск '_'.")
            return
    
    await state.update_data(pattern=pattern)
    
    # Показываем, какие буквы будут скрыты (для типов с выбором вариантов пропускаем)
    morpheme_type = data.get('morpheme_type', '')
    if morpheme_type in ['spelling', 'stress', 'ne_particle']:
        # Для типов с выбором вариантов сразу сохраняем с пустыми скрытыми буквами
        await state.update_data(hidden_letters="")
        
        # Сразу сохраняем слово без запроса скрытых букв
        data = await state.get_data()
        
        # Создаем и сохраняем слово
        async for session in get_session():
            new_word = Word(
                word=data['word'],
                definition="",  # Пустое определение
                explanation=data.get('explanation', ''),
                morpheme_type=data['morpheme_type'],
                puzzle_pattern=data['pattern'],
                hidden_letters="",  # Для типов с выбором вариантов не используется
                difficulty_level=1  # Устанавливаем уровень 1 по умолчанию
            )
            session.add(new_word)
            await session.commit()
            await session.refresh(new_word)
            
            success_text = (
                f"✅ <b>Слово успешно добавлено!</b>\n\n"
                f"📝 Слово: <b>{new_word.word}</b>\n"
                f"🔤 Тип морфемы: <b>{MORPHEME_TYPES[new_word.morpheme_type]}</b>\n"
            )
            
            if new_word.explanation:
                success_text += f"💡 Пояснение: <b>{new_word.explanation}</b>\n"
                
            success_text += f"🧩 Шаблон: <b>{new_word.puzzle_pattern.upper()}</b>\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще слово", callback_data="admin_add_word")],
                [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
            ])
            
            await message.answer(success_text, parse_mode="HTML", reply_markup=keyboard)
            await state.clear()
    else:
        # Для обычных слов показываем скрытые буквы
        hidden_letters = ""
        for i, char in enumerate(pattern):
            if char == '_':
                hidden_letters += word[i]
        
        await message.answer(
            f"✅ Слово: <b>{word}</b>\n"
            f"✅ Шаблон: <b>{pattern.upper()}</b>\n"
            f"✅ Скрытые буквы: <b>{hidden_letters}</b>\n\n"
            f"Теперь введите скрытые буквы точно в том порядке, как они идут в слове.\n"
            f"Для данного шаблона это должно быть: <b>{hidden_letters}</b>\n\n"
            f"Введите скрытые буквы:",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_hidden_letters)

@router.message(AdminStates.waiting_for_hidden_letters)
async def process_hidden_letters(message: Message, state: FSMContext):
    """Обработка скрытых букв"""
    hidden_letters = message.text.strip().lower()
    data = await state.get_data()
    word = data['word']
    pattern = data['pattern']
    
    # Валидация убрана - админ всегда вводит правильно
    
    await state.update_data(hidden_letters=hidden_letters)
    
    # Сразу сохраняем слово без запроса уровня сложности
    data = await state.get_data()
    
    # Создаем и сохраняем слово
    async for session in get_session():
        new_word = Word(
            word=data['word'],
            definition="",  # Пустое определение
            explanation=data.get('explanation', ''),
            morpheme_type=data['morpheme_type'],
            puzzle_pattern=data['pattern'],
            hidden_letters=data['hidden_letters'],
            difficulty_level=1  # Устанавливаем уровень 1 по умолчанию
        )
        session.add(new_word)
        await session.commit()
        await session.refresh(new_word)
        
        success_text = (
            f"✅ <b>Слово успешно добавлено!</b>\n\n"
            f"📝 Слово: <b>{new_word.word}</b>\n"
            f"🔤 Тип морфемы: <b>{MORPHEME_TYPES[new_word.morpheme_type]}</b>\n"
        )
        
        if new_word.explanation:
            success_text += f"💡 Пояснение: <b>{new_word.explanation}</b>\n"
            
        success_text += (
            f"🧩 Шаблон: <b>{new_word.puzzle_pattern.upper()}</b>\n"
            f"🔤 Скрытые буквы: <b>{new_word.hidden_letters}</b>\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще слово", callback_data="admin_add_word")],
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
        ])
        
        await message.answer(success_text, parse_mode="HTML", reply_markup=keyboard)
        await state.clear()

@router.callback_query(F.data == "admin_add_word")
async def callback_add_word(callback: CallbackQuery, state: FSMContext):
    """Коллбэк добавления слова"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "📝 <b>Добавление нового слова</b>\n\n"
        "Введите слово (только буквы):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_word)
    await callback.answer()

@router.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery):
    """Коллбэк возврата в админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.")
        return
    
    await admin_panel_callback(callback)

async def admin_panel_callback(callback: CallbackQuery):
    """Отображение админ-панели через callback"""
    async for session in get_session():
        # Статистика
        total_words_query = select(func.count(Word.id))
        total_words_result = await session.execute(total_words_query)
        total_words = total_words_result.scalar()
        
        total_users_query = select(func.count(User.id))
        total_users_result = await session.execute(total_users_query)
        total_users = total_users_result.scalar()
        
        admin_text = (
            f"👨‍💼 <b>Админ-панель</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"📚 Всего слов: {total_words}\n"
            f"👥 Всего пользователей: {total_users}\n\n"
            f"<b>Доступные команды:</b>\n"
            f"/add_word - Добавить новое слово\n"
            f"/list_words - Список всех слов\n"
            f"/delete_word - Удалить слово\n"
            f"/word_stats - Подробная статистика слов\n"
            f"/user_stats - Статистика пользователей"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить слово", callback_data="admin_add_word")],
            [InlineKeyboardButton(text="📋 Список слов", callback_data="admin_list_words")],
            [InlineKeyboardButton(text="🗑️ Удалить слово", callback_data="admin_delete_word")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
        ])
        
        await callback.message.edit_text(admin_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

@router.message(Command("list_words"))
async def list_words(message: Message):
    """Список всех слов"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    async for session in get_session():
        words_query = select(Word).order_by(Word.id)
        words_result = await session.execute(words_query)
        words = words_result.scalars().all()
        
        if not words:
            await message.answer("📚 В базе данных нет слов.")
            return
        
        words_text = "📋 <b>Список всех слов:</b>\n\n"
        for word in words[:20]:  # Показываем первые 20 слов
            morpheme_name = MORPHEME_TYPES.get(word.morpheme_type, "Неизвестно")
            words_text += (
                f"🆔 <b>{word.id}</b> | "
                f"⭐ <b>{word.difficulty_level}/5</b> | "
                f"🔤 <b>{morpheme_name}</b>\n"
                f"📝 <b>{word.word}</b> → <code>{word.puzzle_pattern.upper()}</code>\n"
                f"📖 {word.definition[:50]}{'...' if len(word.definition) > 50 else ''}\n\n"
            )
        
        if len(words) > 20:
            words_text += f"... и еще {len(words) - 20} слов(а)\n"
        
        await message.answer(words_text, parse_mode="HTML")

async def get_user_statistics():
    """Получает статистику всех пользователей"""
    async for session in get_session():
        stats_text = (
            "📊 <b>Статистика пользователей:</b>\n\n"
            "💡 <i>Слово считается выученным после:</i>\n"
            "   • <i>Прохождения всех 7 интервалов повторения ИЛИ</i>\n"
            "   • <i>5 правильных ответов в тренировках</i>\n\n"
        )
        
        # Получаем всех пользователей
        users_query = select(User).order_by(User.created_at.desc())
        users_result = await session.execute(users_query)
        users = users_result.scalars().all()
        
        if not users:
            stats_text += "📚 В базе данных нет пользователей."
            return stats_text
        
        for user in users:
            # Подсчитываем количество завершенных тренировок
            completed_trainings_query = select(func.count(TrainingSession.id)).where(
                TrainingSession.user_id == user.id,
                TrainingSession.completed_at.isnot(None)
            )
            completed_trainings_result = await session.execute(completed_trainings_query)
            completed_trainings = completed_trainings_result.scalar()
            
            # Подсчитываем количество выученных слов (is_learned = True)
            learned_words_query = select(func.count(UserWord.id)).where(
                UserWord.user_id == user.id,
                UserWord.is_learned == True
            )
            learned_words_result = await session.execute(learned_words_query)
            learned_words = learned_words_result.scalar()
            
            # Подсчитываем слова близкие к изучению (3+ правильных ответов, но не выучены)
            almost_learned_query = select(func.count(UserWord.id)).where(
                UserWord.user_id == user.id,
                UserWord.correct_answers_count >= 3,
                UserWord.is_learned == False
            )
            almost_learned_result = await session.execute(almost_learned_query)
            almost_learned = almost_learned_result.scalar()
            
            # Формируем строку статистики для пользователя
            user_name = user.first_name or user.username or f"ID:{user.telegram_id}"
            stats_text += (
                f"👤 <b>{user_name}</b>\n"
                f"   🎮 Завершенных тренировок: <b>{completed_trainings}</b>\n"
                f"   📚 Выученных слов: <b>{learned_words}</b>\n"
                f"   📈 Близко к изучению: <b>{almost_learned}</b> (7+ прав. ответов)\n"
                f"   📅 Дата регистрации: <b>{user.created_at.strftime('%d.%m.%Y')}</b>\n\n"
            )
        
        return stats_text

@router.message(Command("user_stats"))
async def user_stats(message: Message):
    """Статистика пользователей"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    stats_text = await get_user_statistics()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
    ])
    
    await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)

@router.message(Command("word_stats"))
async def word_stats(message: Message):
    """Статистика слов"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    async for session in get_session():
        # Статистика по типам морфем
        stats_text = "📊 <b>Статистика слов по типам морфем:</b>\n\n"
        
        for morpheme_key, morpheme_name in MORPHEME_TYPES.items():
            count_query = select(func.count(Word.id)).where(Word.morpheme_type == morpheme_key)
            count_result = await session.execute(count_query)
            count = count_result.scalar()
            stats_text += f"🔤 <b>{morpheme_name}:</b> {count} слов\n"
        
        await message.answer(stats_text, parse_mode="HTML")

@router.callback_query(F.data.in_(["admin_list_words", "admin_delete_word", "admin_stats", "admin_user_stats", "admin_word_stats"]))
async def handle_admin_callbacks(callback: CallbackQuery, state: FSMContext):
    """Обработка админских коллбеков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.")
        return
    
    if callback.data == "admin_list_words":
        await list_words_callback(callback)
    elif callback.data == "admin_delete_word":
        await delete_word_callback(callback, state)
    elif callback.data == "admin_stats":
        await stats_callback(callback)
    elif callback.data == "admin_user_stats":
        await user_stats_callback(callback)
    elif callback.data == "admin_word_stats":
        await word_stats_callback(callback)
    else:
        await callback.answer("🚧 Функция в разработке")

async def list_words_callback(callback: CallbackQuery):
    """Список слов через callback"""
    async for session in get_session():
        words_query = select(Word).order_by(Word.id)
        words_result = await session.execute(words_query)
        words = words_result.scalars().all()
        
        if not words:
            await callback.message.edit_text("📚 В базе данных нет слов.")
            return
        
        words_text = "📋 <b>Список всех слов:</b>\n\n"
        for word in words[:15]:  # Показываем первые 15 слов
            morpheme_name = MORPHEME_TYPES.get(word.morpheme_type, "Неизвестно")
            words_text += (
                f"🆔 <b>{word.id}</b> | "
                f"⭐ <b>{word.difficulty_level}/5</b> | "
                f"🔤 <b>{morpheme_name}</b>\n"
                f"📝 <b>{word.word}</b> → <code>{word.puzzle_pattern.upper()}</code>\n\n"
            )
        
        if len(words) > 15:
            words_text += f"... и еще {len(words) - 15} слов(а)\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(words_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

async def stats_callback(callback: CallbackQuery):
    """Статистика через callback - показывает меню выбора типа статистики"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_user_stats")],
        [InlineKeyboardButton(text="📚 Статистика слов", callback_data="admin_word_stats")],
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
    ])
    
    stats_text = (
        "📊 <b>Выбор типа статистики</b>\n\n"
        "Выберите какую статистику вы хотите посмотреть:"
    )
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

async def user_stats_callback(callback: CallbackQuery):
    """Статистика пользователей через callback"""
    stats_text = await get_user_statistics()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Статистика слов", callback_data="admin_word_stats")],
        [InlineKeyboardButton(text="🔙 К выбору статистики", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🏠 Админ-панель", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

async def word_stats_callback(callback: CallbackQuery):
    """Статистика слов через callback"""
    async for session in get_session():
        # Статистика по типам морфем
        stats_text = "📊 <b>Статистика слов по типам морфем:</b>\n\n"
        
        for morpheme_key, morpheme_name in MORPHEME_TYPES.items():
            count_query = select(func.count(Word.id)).where(Word.morpheme_type == morpheme_key)
            count_result = await session.execute(count_query)
            count = count_result.scalar()
            stats_text += f"🔤 <b>{morpheme_name}:</b> {count} слов\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_user_stats")],
            [InlineKeyboardButton(text="🔙 К выбору статистики", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🏠 Админ-панель", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

@router.message(Command("delete_word"))
async def start_delete_word(message: Message, state: FSMContext):
    """Начало процесса удаления слова"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    await message.answer(
        "🗑️ <b>Удаление слова</b>\n\n"
        "Введите слово для удаления:\n"
        "<i>Например: библиотека</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_word_to_delete)

async def delete_word_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса удаления слова через callback"""
    await callback.message.edit_text(
        "🗑️ <b>Удаление слова</b>\n\n"
        "Введите слово для удаления:\n"
        "<i>Например: библиотека</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_word_to_delete)
    await callback.answer()

@router.message(AdminStates.waiting_for_word_to_delete)
async def process_word_deletion(message: Message, state: FSMContext):
    """Обработка удаления слова"""
    word_text = message.text.strip()  # НЕ применяем .lower() чтобы сохранить ударения!
    
    # Проверяем корректность слова (разрешаем русские и английские буквы, дефисы, пробелы)
    import re
    if not re.match(r'^[а-яёА-ЯЁa-zA-Z\-\s]+$', word_text) or len(word_text) < 2:
        await message.answer("❌ Введите корректное слово (буквы, дефисы, пробелы, минимум 2 символа).")
        return
    
    async for session in get_session():
        # Сначала ищем точное совпадение (с ударениями)
        word_query = select(Word).where(Word.word == word_text)
        word_result = await session.execute(word_query)
        word = word_result.scalar_one_or_none()
        
        # Если не найдено точное совпадение, ищем без учета регистра (для совместимости)
        if not word:
            word_query_lower = select(Word).where(Word.word.ilike(word_text))
            word_result_lower = await session.execute(word_query_lower)
            word = word_result_lower.scalar_one_or_none()
        
        if not word:
            await message.answer(f"❌ Слово '{word_text}' не найдено в базе данных.")
            return
        
        # Показываем информацию о слове и просим подтверждение
        morpheme_name = MORPHEME_TYPES.get(word.morpheme_type, "Неизвестно")
        confirmation_text = (
            f"🗑️ <b>Подтвердите удаление:</b>\n\n"
            f"📝 Слово: <b>{word.word}</b>\n"
            f"🔤 Тип морфемы: <b>{morpheme_name}</b>\n"
            f"🧩 Шаблон: <code>{word.puzzle_pattern.upper()}</code>\n"
        )
        
        if word.explanation:
            confirmation_text += f"💡 Пояснение: <b>{word.explanation}</b>\n"
        
        confirmation_text += f"\n❗ <b>Внимание:</b> Это действие нельзя отменить!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{word.id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])
        
        await message.answer(confirmation_text, parse_mode="HTML", reply_markup=keyboard)
        await state.clear()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_word_deletion(callback: CallbackQuery):
    """Подтверждение удаления слова"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.")
        return
    
    word_id = int(callback.data.replace("confirm_delete_", ""))
    
    async for session in get_session():
        word_query = select(Word).where(Word.id == word_id)
        word_result = await session.execute(word_query)
        word = word_result.scalar_one_or_none()
        
        if not word:
            await callback.message.edit_text("❌ Слово не найдено.")
            return
        
        word_name = word.word
        
        # Удаляем связанные записи из user_words
        from database.models import UserWord
        user_words_query = select(UserWord).where(UserWord.word_id == word_id)
        user_words_result = await session.execute(user_words_query)
        user_words = user_words_result.scalars().all()
        
        for user_word in user_words:
            await session.delete(user_word)
        
        # Удаляем само слово
        await session.delete(word)
        await session.commit()
        
        success_text = (
            f"✅ <b>Слово успешно удалено!</b>\n\n"
            f"📝 Удалено: <b>{word_name}</b>\n"
            f"🗑️ Также удалены все связанные записи из личных словарей пользователей"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer() 