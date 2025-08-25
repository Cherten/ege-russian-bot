from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from database.models import Word, User, UserWord
import random
from config import WORDS_PER_TRAINING

class WordService:
    
    @staticmethod
    def create_word_puzzle(word: Word) -> Tuple[str, str]:
        """
        Создает загадку из слова, используя предустановленный администратором шаблон
        Возвращает: (слово_с_пропусками, правильный_ответ)
        """
        if word.morpheme_type == 'spelling':
            # Для слов написания возвращаем паттерн и правильный ответ
            return word.puzzle_pattern, word.word
        elif word.morpheme_type == 'stress':
            # Для ударений показываем ученику слово БЕЗ ударения в вопросе, 
            # но правильный ответ остается с ударением
            import re
            # Создаем базовое слово без ударения из puzzle_pattern (все строчными)
            base_word = re.sub(r'\(([А-ЯЁа-яё])\)', r'\1', word.puzzle_pattern).lower()
            return base_word, word.word
        elif word.morpheme_type == 'ne_particle':
            # Для частицы НЕ возвращаем паттерн и правильный ответ
            return word.puzzle_pattern, word.word
        else:
            # Для типов с вводом букв (roots, prefixes, endings, n_nn, suffix) - стандартная логика
            puzzle_pattern = word.puzzle_pattern
            correct_answer = word.hidden_letters
            return puzzle_pattern, correct_answer
    
    @staticmethod
    def create_spelling_options(word: Word) -> List[str]:
        """
        Создает варианты ответов для слов написания
        Возвращает список из 3 вариантов: правильный + 2 неправильных
        """
        if word.morpheme_type not in ['spelling', 'stress', 'ne_particle']:
            return []
        
        correct_answer = word.word
        
        # Извлекаем часть в скобках
        import re
        match = re.search(r'\(([^)]+)\)', word.puzzle_pattern)
        if not match:
            return [correct_answer]
        
        prefix_part = match.group(1)  # часть в скобках
        base_part = word.puzzle_pattern.replace(f'({prefix_part})', '')  # остальная часть
        
        # Создаем варианты
        options = []
        
        # 1. Правильный вариант (уже есть в word.word)
        options.append(correct_answer)
        
        # 2. Слитное написание
        if correct_answer != prefix_part + base_part:
            options.append(prefix_part + base_part)
        
        # 3. Раздельное написание  
        if correct_answer != f"{prefix_part} {base_part}":
            options.append(f"{prefix_part} {base_part}")
        
        # 4. Дефисное написание
        if correct_answer != f"{prefix_part}-{base_part}":
            options.append(f"{prefix_part}-{base_part}")
        
        # Берем только первые 3 варианта и перемешиваем
        options = list(set(options))  # Убираем дубликаты
        options = options[:3]
        
        # Дополняем до 3 вариантов, если нужно
        while len(options) < 3:
            options.append(f"{prefix_part} {base_part} (вариант {len(options)})")
        
        random.shuffle(options)
        return options
    
    @staticmethod
    def create_stress_options(word: Word) -> List[str]:
        """
        Создает варианты ответов для слов с ударениями
        word.word = "нефтепровОд" (правильный ответ с ударением)
        word.puzzle_pattern = "нефтепр(О)в(О)д" (шаблон с возможными ударениями)
        Возвращает: ["нефтепрОвод", "нефтепровОд"] - ТОЛЬКО варианты из шаблона
        """
        if word.morpheme_type != 'stress':
            return []
        
        pattern = word.puzzle_pattern  # нефтепр(О)в(О)д
        
        import re
        
        # Создаем базовое слово без ударения (все строчными)
        base_word = re.sub(r'\(([А-ЯЁа-яё])\)', r'\1', pattern).lower()  # нефтепровод
        
        options = []  # Список для вариантов ударения
        
        # Находим все позиции букв в скобках и создаем варианты ударений
        pattern_pos = 0
        base_word_pos = 0
        
        while pattern_pos < len(pattern):
            char = pattern[pattern_pos]
            
            if char == '(':
                # Находим закрывающую скобку
                close_pos = pattern.find(')', pattern_pos)
                if close_pos != -1:
                    # Извлекаем букву из скобок
                    stressed_letter = pattern[pattern_pos + 1:close_pos]
                    
                    # Создаем вариант с ударением на этой позиции
                    variant = list(base_word)
                    if base_word_pos < len(variant):
                        variant[base_word_pos] = stressed_letter.upper()
                        variant_word = ''.join(variant)
                        
                        # Добавляем только если такого варианта еще нет
                        if variant_word not in options:
                            options.append(variant_word)
                    
                    # Переходим за закрывающую скобку
                    pattern_pos = close_pos + 1
                    base_word_pos += 1
                else:
                    # Некорректный паттерн, пропускаем
                    pattern_pos += 1
            else:
                # Обычный символ, просто переходим дальше
                pattern_pos += 1
                base_word_pos += 1
        
        # Перемешиваем варианты
        random.shuffle(options)
        return options
    
    @staticmethod
    def create_ne_particle_options(word: Word) -> List[str]:
        """
        Создает варианты ответов для слов с частицей НЕ
        Пример: "(не)красивый" -> ["некрасивый", "не красивый"]
        """
        if word.morpheme_type != 'ne_particle':
            return []
        
        correct_answer = word.word
        
        # Извлекаем часть с НЕ в скобках
        import re
        match = re.search(r'\(не\)(.+)', word.puzzle_pattern, re.IGNORECASE)
        if not match:
            return [correct_answer]
        
        base_part = match.group(1).strip()  # остальная часть слова
        
        options = []
        
        # 1. Правильный вариант
        options.append(correct_answer)
        
        # 2. Слитное написание
        slitno = f"не{base_part}"
        if correct_answer != slitno:
            options.append(slitno)
        
        # 3. Раздельное написание
        razdelno = f"не {base_part}"
        if correct_answer != razdelno:
            options.append(razdelno)
        
        # Убираем дубликаты и берем первые 3
        options = list(set(options))[:3]
        
        # Дополняем до 2 вариантов минимум
        while len(options) < 2:
            options.append(f"не {base_part} (вариант)")
        
        random.shuffle(options)
        return options
    
    @staticmethod
    def create_options_for_word(word: Word) -> List[str]:
        """
        Универсальная функция для создания вариантов ответов в зависимости от типа морфемы
        """
        if word.morpheme_type == 'spelling':
            return WordService.create_spelling_options(word)
        elif word.morpheme_type == 'stress':
            return WordService.create_stress_options(word)
        elif word.morpheme_type == 'ne_particle':
            return WordService.create_ne_particle_options(word)
        else:
            # Для типов с вводом букв (roots, prefixes, endings, n_nn, suffix)
            return []
    
    @staticmethod
    def validate_word_pattern(word: str, pattern: str, hidden_letters: str) -> bool:
        """
        Проверяет корректность шаблона слова
        """
        if len(word) != len(pattern):
            return False
        
        # Проверяем, что количество пропусков совпадает с количеством скрытых букв
        underscore_count = pattern.count('_')
        if underscore_count != len(hidden_letters):
            return False
        
        # Проверяем, что видимые буквы в шаблоне совпадают с оригинальным словом
        hidden_index = 0
        for i, char in enumerate(pattern):
            if char == '_':
                if hidden_index >= len(hidden_letters):
                    return False
                if word[i].lower() != hidden_letters[hidden_index].lower():
                    return False
                hidden_index += 1
            else:
                if word[i].lower() != char.lower():
                    return False
        
        return True
    
    @staticmethod
    async def get_training_words(session: Session, user_id: int) -> List[Word]:
        """
        Получает слова для тренировки (новые слова + слова для повторения)
        """
        # Получаем слова для повторения из личного словаря
        repetition_words_query = select(Word).join(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.next_repetition <= func.now(),
            UserWord.is_learned == False
        ).limit(WORDS_PER_TRAINING // 2)
        
        repetition_words = await session.execute(repetition_words_query)
        repetition_words = repetition_words.scalars().all()
        
        # Если слов для повторения мало, добавляем новые слова
        remaining_slots = WORDS_PER_TRAINING - len(repetition_words)
        
        if remaining_slots > 0:
            # Получаем новые слова, которых нет в личном словаре пользователя
            new_words_query = select(Word).where(
                ~Word.id.in_(
                    select(UserWord.word_id).where(UserWord.user_id == user_id)
                )
            ).order_by(func.random()).limit(remaining_slots)
            
            new_words = await session.execute(new_words_query)
            new_words = new_words.scalars().all()
            
            return list(repetition_words) + list(new_words)
        
        return list(repetition_words)
    
    @staticmethod
    async def get_training_words_by_morpheme(session: Session, user_id: int, morpheme_type: str) -> List[Word]:
        """
        Получает слова для тренировки по определенному типу морфемы
        """
        # Получаем слова для повторения из личного словаря с фильтром по типу морфемы
        repetition_words_query = select(Word).join(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.next_repetition <= func.now(),
            UserWord.is_learned == False,
            Word.morpheme_type == morpheme_type
        ).limit(WORDS_PER_TRAINING // 2)
        
        repetition_words = await session.execute(repetition_words_query)
        repetition_words = repetition_words.scalars().all()
        
        # Если слов для повторения мало, добавляем новые слова того же типа
        remaining_slots = WORDS_PER_TRAINING - len(repetition_words)
        
        if remaining_slots > 0:
            # Получаем новые слова определенного типа, которых нет в личном словаре пользователя
            new_words_query = select(Word).where(
                Word.morpheme_type == morpheme_type,
                ~Word.id.in_(
                    select(UserWord.word_id).where(UserWord.user_id == user_id)
                )
            ).order_by(func.random()).limit(remaining_slots)
            
            new_words = await session.execute(new_words_query)
            new_words = new_words.scalars().all()
            
            return list(repetition_words) + list(new_words)
        
        return list(repetition_words)
    
    @staticmethod
    async def get_learned_words_by_morpheme(session: Session, user_id: int, morpheme_type: str) -> List[Word]:
        """
        Получает ВЫУЧЕННЫЕ слова для повторения по определенному типу морфемы
        """
        from config import WORDS_PER_TRAINING
        
        # Получаем выученные слова определенного типа морфемы
        learned_words_query = select(Word).join(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.is_learned == True,  # ВЫУЧЕННЫЕ слова
            Word.morpheme_type == morpheme_type
        ).order_by(func.random()).limit(WORDS_PER_TRAINING)
        
        learned_words = await session.execute(learned_words_query)
        learned_words = learned_words.scalars().all()
        
        return list(learned_words)
    
    @staticmethod
    async def get_all_learned_words(session: Session, user_id: int) -> List[Word]:
        """
        Получает ВСЕ выученные слова для смешанной тренировки
        """
        from config import WORDS_PER_TRAINING
        
        # Получаем все выученные слова пользователя
        learned_words_query = select(Word).join(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.is_learned == True  # ВЫУЧЕННЫЕ слова
        ).order_by(func.random()).limit(WORDS_PER_TRAINING)
        
        learned_words = await session.execute(learned_words_query)
        learned_words = learned_words.scalars().all()
        
        return list(learned_words)

    @staticmethod
    def check_answer(puzzle: str, user_answer: str, correct_answer: str) -> bool:
        """
        Проверяет правильность ответа пользователя
        """
        # Убираем лишние пробелы и приводим к нижнему регистру
        user_answer = user_answer.strip().lower()
        correct_answer = correct_answer.lower()
        
        return user_answer == correct_answer
    
    @staticmethod
    async def add_word_to_user_dictionary(session: Session, user_id: int, word_id: int):
        """
        Добавляет слово в личный словарь пользователя после ошибки
        """
        from datetime import datetime, timedelta
        from config import REPETITION_INTERVALS
        
        # Проверяем, есть ли уже это слово в словаре пользователя
        existing_query = select(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.word_id == word_id
        )
        existing = await session.execute(existing_query)
        existing_word = existing.scalar_one_or_none()
        
        if existing_word:
            # Увеличиваем счетчик ошибок и сбрасываем интервал
            existing_word.mistakes_count += 1
            existing_word.current_interval_index = 0
            existing_word.next_repetition = datetime.utcnow() + timedelta(minutes=REPETITION_INTERVALS[0])
            existing_word.last_reviewed = datetime.utcnow()
        else:
            # Создаем новую запись
            new_user_word = UserWord(
                user_id=user_id,
                word_id=word_id,
                mistakes_count=1,
                current_interval_index=0,
                next_repetition=datetime.utcnow() + timedelta(minutes=REPETITION_INTERVALS[0])
            )
            session.add(new_user_word)
        
        await session.commit()
    
    @staticmethod
    async def update_word_progress(session: Session, user_id: int, word_id: int, is_correct: bool):
        """
        Обновляет прогресс изучения слова
        Слово считается выученным при:
        1) Прохождении всех 7 интервалов повторения ИЛИ
        2) После 10 правильных ответов в тренировках
        """
        from datetime import datetime, timedelta
        from config import REPETITION_INTERVALS
        
        user_word_query = select(UserWord).where(
            UserWord.user_id == user_id,
            UserWord.word_id == word_id
        )
        user_word = await session.execute(user_word_query)
        user_word = user_word.scalar_one_or_none()
        
        if not user_word:
            return
            
        user_word.last_reviewed = datetime.utcnow()
        
        if is_correct:
            # Увеличиваем счетчик правильных ответов
            user_word.correct_answers_count += 1
            
            # Переходим к следующему интервалу
            next_interval_index = min(
                user_word.current_interval_index + 1,
                len(REPETITION_INTERVALS) - 1
            )
            user_word.current_interval_index = next_interval_index
            
            # Проверяем условия для пометки слова как выученного:
            # 1) Прошли все интервалы ИЛИ 2) Дали 10 правильных ответов
            if (next_interval_index == len(REPETITION_INTERVALS) - 1) or (user_word.correct_answers_count >= 10):
                user_word.is_learned = True
                
            user_word.next_repetition = datetime.utcnow() + timedelta(
                minutes=REPETITION_INTERVALS[next_interval_index]
            )
        else:
            # При ошибке сбрасываем интервал на начало и увеличиваем счетчик ошибок
            # Счетчик правильных ответов НЕ сбрасываем, так как это независимый критерий
            user_word.current_interval_index = 0
            user_word.mistakes_count += 1
            user_word.next_repetition = datetime.utcnow() + timedelta(
                minutes=REPETITION_INTERVALS[0]
            )
        
        await session.commit() 