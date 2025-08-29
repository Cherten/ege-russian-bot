import random
from typing import List

class SupportPhrasesService:
    """Сервис для работы с поддерживающими фразами"""
    
    def __init__(self):
        self._phrases = self._load_phrases()
    
    def _load_phrases(self) -> List[str]:
        """Загружает список поддерживающих фраз из файла"""
        try:
            with open("список поддерживающих фраз.txt", "r", encoding="utf-8") as file:
                phrases = []
                for line in file:
                    phrase = line.strip()
                    if phrase:  # Игнорируем пустые строки
                        phrases.append(phrase)
                return phrases
        except FileNotFoundError:
            # Запасной список фраз на случай отсутствия файла
            return [
                "У тебя всё получится 💪",
                "Отличная работа ✅",
                "Вперёд 🚀",
                "Ты справишься 👍",
                "Так держать 🌟",
                "Хороший результат ✔️",
                "Продолжай 💡",
                "Отлично идёшь 📈",
                "Верное решение ✅",
                "Отличный выбор 🌿"
            ]
    
    def get_random_phrase(self) -> str:
        """Возвращает случайную поддерживающую фразу"""
        return random.choice(self._phrases)
    
    def should_show_support_phrase(self, words_answered: int) -> bool:
        """Определяет, нужно ли показать поддерживающую фразу
        
        Args:
            words_answered: количество отвеченных слов
            
        Returns:
            True если нужно показать фразу (каждые 3 слова)
        """
        return words_answered > 0 and words_answered % 3 == 0
    
    def get_support_message(self) -> str:
        """Возвращает отформатированное сообщение с поддерживающей фразой"""
        phrase = self.get_random_phrase()
        return f"{phrase}"

# Создаем глобальный экземпляр сервиса
support_phrases_service = SupportPhrasesService()
