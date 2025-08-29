import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def migrate_correct_answers_count():
    """Миграция для добавления поля correct_answers_count в таблицу user_words"""
    
    async for session in get_session():
        try:
            # Проверяем, существует ли уже столбец
            result = await session.execute(text("PRAGMA table_info(user_words);"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем столбец correct_answers_count, если его нет
            if 'correct_answers_count' not in column_names:
                await session.execute(text("ALTER TABLE user_words ADD COLUMN correct_answers_count INTEGER NOT NULL DEFAULT 0;"))
                print("✅ Добавлен столбец 'correct_answers_count'")
                
                # Обновляем существующие записи, устанавливая счетчик в 0
                await session.execute(text("UPDATE user_words SET correct_answers_count = 0 WHERE correct_answers_count IS NULL;"))
                print("✅ Обновлены существующие записи")
                
            else:
                print("ℹ️ Столбец 'correct_answers_count' уже существует")
            
            await session.commit()
            print("\n🎉 Миграция успешно выполнена!")
            print("📚 Теперь слова будут считаться выученными после:")
            print("   1) Прохождения всех 7 интервалов повторения ИЛИ")
            print("   2) 5 правильных ответов в тренировках")
            
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            await session.rollback()
            raise

async def main():
    print("🔄 Запуск миграции для добавления счетчика правильных ответов...\n")
    await migrate_correct_answers_count()

if __name__ == "__main__":
    asyncio.run(main()) 