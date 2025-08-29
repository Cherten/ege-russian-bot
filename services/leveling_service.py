from typing import List, Tuple, Optional
from sqlalchemy import select, desc, func
from database.models import User, UserWord, Word
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

class LevelingService:
    """Сервис для работы с системой уровней и опыта"""
    
    def __init__(self):
        self._level_names = self._load_level_names()
        self._experience_thresholds = self._calculate_experience_thresholds()
    
    def _load_level_names(self) -> List[str]:
        """Загружает названия уровней из файла"""
        try:
            with open("названия уровней.txt", "r", encoding="utf-8") as file:
                names = []
                for line in file:
                    # Убираем номер и точку в начале строки
                    name = line.strip()
                    if name and name[0].isdigit():
                        # Находим первую точку или табуляцию и берем текст после неё
                        if '\t' in name:
                            name = name.split('\t', 1)[1]
                        elif '.' in name:
                            name = name.split('.', 1)[1].strip()
                    names.append(name)
                return names
        except FileNotFoundError:
            # Запасные названия уровней
            return [
                "Новичок", "Ученик", "Знаток", "Эксперт", "Мастер",
                "Гуру", "Легенда", "Чемпион", "Герой", "Титан",
                "Божество", "Абсолют", "Космос", "Вселенная", "Бесконечность",
                "Вечность", "Совершенство", "Идеал", "Недостижимый", "Невозможный",
                "Фантастический", "Мифический", "Легендарный", "Эпический", "Величайший"
            ]
    
    def _calculate_experience_thresholds(self) -> List[int]:
        """Рассчитывает пороги опыта для каждого уровня"""
        thresholds = [0]  # Уровень 1 начинается с 0 опыта
        
        # Прогрессивное увеличение опыта для каждого уровня
        # Разные формулы для низких и высоких уровней
        base_exp = 100
        
        for level in range(2, 26):  # уровни 2-25
            if level <= 10:
                # Для низких уровней (2-10): стандартная прогрессия
                exp_needed = int(base_exp * (level ** 1.5) + (level - 1) * 50)
            elif level <= 15:
                # Для средних уровней (11-15): умеренное увеличение сложности
                exp_needed = int(base_exp * (level ** 1.8) + (level - 1) * 100)
            else:
                # Для высоких уровней (16-25): умеренный экспоненциальный рост
                exp_needed = int(base_exp * (level ** 1.9) + (level - 1) * 150)
            
            thresholds.append(thresholds[-1] + exp_needed)
        
        return thresholds
    
    def get_level_name(self, level: int) -> str:
        """Возвращает название уровня по номеру"""
        if 1 <= level <= len(self._level_names):
            return self._level_names[level - 1]
        return f"Уровень {level}"
    
    def get_level_by_experience(self, experience: int) -> int:
        """Определяет уровень по количеству опыта"""
        level = 1
        for i, threshold in enumerate(self._experience_thresholds):
            if experience >= threshold:
                level = i + 1
            else:
                break
        return min(level, 25)  # Максимальный уровень 25
    
    def get_experience_for_next_level(self, current_level: int) -> int:
        """Возвращает количество опыта, необходимое для следующего уровня"""
        if current_level >= 25:
            return 0  # Максимальный уровень достигнут
        
        return self._experience_thresholds[current_level]
    
    def get_experience_progress(self, experience: int, level: int) -> Tuple[int, int]:
        """Возвращает прогресс опыта: (текущий_опыт_уровня, опыт_до_следующего_уровня)"""
        if level >= 25:
            return (experience, 0)
        
        level_start = self._experience_thresholds[level - 1] if level > 1 else 0
        level_end = self._experience_thresholds[level]
        
        current_progress = experience - level_start
        total_needed = level_end - level_start
        
        return (current_progress, total_needed)
    
    def calculate_experience_reward(self, difficulty_level: int = 1, streak: int = 0) -> int:
        """Рассчитывает награду опыта за правильный ответ"""
        base_reward = 10  # Базовая награда
        difficulty_bonus = difficulty_level * 2  # Бонус за сложность
        streak_bonus = min(streak, 10) * 1  # Бонус за серию (максимум 10)
        
        return base_reward + difficulty_bonus + streak_bonus
    
    async def add_experience(self, session: AsyncSession, user: User, experience: int) -> Tuple[bool, int]:
        """
        Добавляет опыт пользователю
        Возвращает (level_up_occurred, new_level)
        """
        old_level = user.level
        user.experience_points += experience
        
        new_level = self.get_level_by_experience(user.experience_points)
        user.level = new_level
        
        await session.commit()
        
        return (new_level > old_level, new_level)
    
    async def update_streak(self, session: AsyncSession, user: User) -> Tuple[int, bool]:
        """
        Обновляет стрик пользователя при завершении тренировки
        Возвращает (новый_стрик, новый_рекорд)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Если пользователь уже занимался сегодня, стрик не меняется
        if user.last_training_date == today:
            return user.current_streak, False
        
        # Если последняя тренировка была вчера - продолжаем стрик
        if user.last_training_date == yesterday:
            user.current_streak += 1
        # Если была большая пауза - начинаем стрик заново
        elif user.last_training_date is None or user.last_training_date < yesterday:
            user.current_streak = 1
        else:
            # Если последняя тренировка была сегодня, ничего не делаем
            return user.current_streak, False
        
        # Обновляем дату последней тренировки
        user.last_training_date = today
        
        # Проверяем, не побили ли рекорд
        new_record = False
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak
            new_record = True
        
        await session.commit()
        
        return user.current_streak, new_record
    
    async def get_leaderboard(self, session: AsyncSession, limit: int = 10) -> List[Tuple[User, str]]:
        """Возвращает топ пользователей по уровню и опыту"""
        query = select(User).where(User.is_active == True).order_by(
            desc(User.level),
            desc(User.experience_points)
        ).limit(limit)
        
        result = await session.execute(query)
        users = result.scalars().all()
        
        leaderboard = []
        for user in users:
            level_name = self.get_level_name(user.level)
            leaderboard.append((user, level_name))
        
        return leaderboard
    
    async def format_user_stats(self, user: User, session: AsyncSession) -> str:
        """Форматирует статистику пользователя"""
        level_name = self.get_level_name(user.level)
        current_exp, needed_exp = self.get_experience_progress(user.experience_points, user.level)
        
        # Получаем статистику по словам
        total_words_query = select(func.count(Word.id))
        total_words_result = await session.execute(total_words_query)
        total_words = total_words_result.scalar() or 0
        
        learned_words_query = select(func.count(UserWord.id)).where(
            UserWord.user_id == user.id,
            UserWord.is_learned == True
        )
        learned_words_result = await session.execute(learned_words_query)
        learned_words = learned_words_result.scalar() or 0
        
        # Рассчитываем процент выученных слов
        if total_words > 0:
            learned_percentage = (learned_words / total_words) * 100
        else:
            learned_percentage = 0.0
        
        stats = f"🎯 <b>Ваша статистика:</b>\n\n"
        stats += f"🏆 <b>Уровень:</b> {user.level} - {level_name}\n"
        stats += f"⭐ <b>Опыт:</b> {user.experience_points}\n"
        stats += f"🔥 <b>Стрик:</b> {user.current_streak} дн. (рекорд: {user.best_streak} дн.)\n"
        stats += f"📚 <b>Изучено слов:</b> {learned_words} из {total_words} ({learned_percentage:.1f}%)\n"
        
        # Добавляем полосу прогресса для изучения слов
        if total_words > 0:
            words_progress_bar = self._create_progress_bar(learned_words, total_words)
            stats += f"📊 <b>Прогресс изучения:</b> {words_progress_bar}\n"
        
        stats += "\n"
        
        if user.level < 25:
            progress_bar = self._create_progress_bar(current_exp, needed_exp)
            stats += f"📈 <b>Прогресс уровня:</b> {current_exp}/{needed_exp}\n"
            stats += f"{progress_bar}\n"
            stats += f"🎯 До следующего уровня: {needed_exp - current_exp} опыта"
        else:
            stats += f"🌟 <b>Поздравляем! Достигнут максимальный уровень!</b>"
        
        return stats
    
    def _create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Создает визуальную полосу прогресса"""
        if total == 0:
            return "🟩" * length
        
        filled = int((current / total) * length)
        empty = length - filled
        
        return "🟩" * filled + "⬜" * empty

# Создаем глобальный экземпляр сервиса
leveling_service = LevelingService()
