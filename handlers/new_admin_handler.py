from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, delete
from database.database import get_session
from database.models import Word, User
from services.word_service import WordService
from config import ADMIN_ID, MORPHEME_TYPES

router = Router()

class AdminStates(StatesGroup):
    waiting_for_word = State()
    waiting_for_definition = State()
    waiting_for_morpheme_type = State()
    waiting_for_explanation = State()
    waiting_for_pattern = State()
    waiting_for_hidden_letters = State()
    waiting_for_difficulty = State()
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
    
    await message.answer(
        f"✅ Слово: <b>{word}</b>\n\n"
        f"Введите определение слова:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_definition)

@router.message(AdminStates.waiting_for_definition)
async def process_definition(message: Message, state: FSMContext):
    """Обработка определения слова"""
    definition = message.text.strip()
    
    if len(definition) < 5:
        await message.answer("❌ Определение должно содержать минимум 5 символов.")
        return
    
    await state.update_data(definition=definition)
    data = await state.get_data()
    
    # Создаем клавиатуру выбора типа морфемы
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
        f"✅ Слово: <b>{data['word']}</b>\n"
        f"✅ Определение: <b>{definition}</b>\n\n"
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
        f"✅ Определение: <b>{data['definition']}</b>\n"
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
        f"✅ Определение: <b>{data['definition']}</b>\n"
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
    pattern = message.text.strip().lower()
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
    
    # Показываем, какие буквы будут скрыты (для слов написания пропускаем)
    morpheme_type = data.get('morpheme_type', '')
    if morpheme_type == 'spelling':
        # Для слов написания сразу переходим к сохранению с пустыми скрытыми буквами
        await state.update_data(hidden_letters="")
        await message.answer(
            f"✅ Слово: <b>{word}</b>\n"
            f"✅ Шаблон: <b>{pattern.upper()}</b>\n\n"
            f"Для слов написания поле 'скрытые буквы' не используется.\n"
            f"Введите уровень сложности (1-5):",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_difficulty)
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
    await message.answer(
        f"✅ Слово: <b>{word}</b>\n"
        f"✅ Шаблон: <b>{pattern.upper()}</b>\n"
        f"✅ Скрытые буквы: <b>{hidden_letters}</b>\n\n"
        f"Введите уровень сложности (1-5):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_difficulty)

@router.message(AdminStates.waiting_for_difficulty)
async def process_difficulty(message: Message, state: FSMContext):
    """Обработка уровня сложности"""
    try:
        difficulty = int(message.text.strip())
        if difficulty < 1 or difficulty > 5:
            await message.answer("❌ Уровень сложности должен быть от 1 до 5.")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 5.")
        return
    
    data = await state.get_data()
    
    # Создаем и сохраняем слово
    async for session in get_session():
        new_word = Word(
            word=data['word'],
            definition=data['definition'],
            explanation=data.get('explanation', ''),
            morpheme_type=data['morpheme_type'],
            puzzle_pattern=data['pattern'],
            hidden_letters=data['hidden_letters'],
            difficulty_level=difficulty
        )
        session.add(new_word)
        await session.commit()
        await session.refresh(new_word)
        
        success_text = (
            f"✅ <b>Слово успешно добавлено!</b>\n\n"
            f"📝 Слово: <b>{new_word.word}</b>\n"
            f"📖 Определение: <b>{new_word.definition}</b>\n"
            f"🔤 Тип морфемы: <b>{MORPHEME_TYPES[new_word.morpheme_type]}</b>\n"
        )
        
        if new_word.explanation:
            success_text += f"💡 Пояснение: <b>{new_word.explanation}</b>\n"
            
        success_text += (
            f"🧩 Шаблон: <b>{new_word.puzzle_pattern.upper()}</b>\n"
            f"🔤 Скрытые буквы: <b>{new_word.hidden_letters}</b>\n"
            f"⭐ Сложность: <b>{new_word.difficulty_level}/5</b>\n"
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