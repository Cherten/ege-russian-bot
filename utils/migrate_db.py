"""
Утилита для миграции базы данных при обновлении структуры Word модели
"""
import asyncio
import sys
import os

# Добавляем родительскую директорию в sys.path для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import init_db, get_session
from database.models import Word
from sqlalchemy import select, func

async def migrate_database():
    """Обновляет структуру базы данных"""
    print("🔄 Инициализация базы данных с новой структурой...")
    await init_db()
    
    async for session in get_session():
        # Проверяем, есть ли старые записи без новых полей
        try:
            words_query = select(func.count(Word.id))
            result = await session.execute(words_query)
            count = result.scalar()
            print(f"📊 Найдено записей в таблице words: {count}")
            
            if count > 0:
                print("⚠️ Обнаружены старые записи. Они могут быть несовместимы с новой структурой.")
                print("📝 Новые слова нужно будет добавить через админ-панель бота.")
                
        except Exception as e:
            print(f"ℹ️ Создается новая структура базы данных: {e}")
    
    print("✅ Миграция завершена!")
    print("\n📋 Следующие шаги:")
    print("1. Запустите бота: python main.py")
    print("2. Используйте команду /admin для доступа к админ-панели")
    print("3. Добавьте словарные слова через /add_word")
    print("\n💡 Пример добавления слова:")
    print("   Слово: апельсин")
    print("   Определение: Цитрусовый фрукт оранжевого цвета")
    print("   Шаблон: ап_льс_н")
    print("   Скрытые буквы: еи")
    print("   Сложность: 2")

if __name__ == "__main__":
    try:
        asyncio.run(migrate_database())
    except KeyboardInterrupt:
        print("\n👋 Миграция прервана пользователем") 