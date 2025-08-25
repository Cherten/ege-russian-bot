import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def migrate_morpheme_types():
    """Миграция для добавления полей explanation и morpheme_type"""
    
    async for session in get_session():
        try:
            # Проверяем, существуют ли уже столбцы
            result = await session.execute(text("PRAGMA table_info(words);"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем столбец explanation, если его нет
            if 'explanation' not in column_names:
                await session.execute(text("ALTER TABLE words ADD COLUMN explanation TEXT;"))
                print("✅ Добавлен столбец 'explanation'")
            else:
                print("ℹ️ Столбец 'explanation' уже существует")
            
            # Добавляем столбец morpheme_type, если его нет
            if 'morpheme_type' not in column_names:
                await session.execute(text("ALTER TABLE words ADD COLUMN morpheme_type VARCHAR(50) NOT NULL DEFAULT 'roots';"))
                print("✅ Добавлен столбец 'morpheme_type'")
            else:
                print("ℹ️ Столбец 'morpheme_type' уже существует")
            
            await session.commit()
            print("\n🎉 Миграция успешно выполнена!")
            
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            await session.rollback()
            raise

async def main():
    print("🔄 Запуск миграции для поддержки типов морфем...\n")
    await migrate_morpheme_types()

if __name__ == "__main__":
    asyncio.run(main()) 