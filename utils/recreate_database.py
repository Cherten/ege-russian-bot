import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session, init_db

async def recreate_database():
    """Пересоздает базу данных с обновленной структурой"""
    
    print("🔄 Пересоздание базы данных vocabulary_bot.db с новой структурой...\n")
    
    try:
        # Удаляем старую базу данных, если она существует
        db_path = "../vocabulary_bot.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            print("🗑️  Удалена старая база данных")
        
        # Создаем новую базу данных со всеми таблицами
        print("📦 Создание новых таблиц...")
        await init_db()
        print("✅ Таблицы созданы успешно!")
        
        # Проверяем структуру созданных таблиц
        async for session in get_session():
            print("\n📋 Проверка созданных таблиц:")
            
            # Получаем список всех таблиц
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            
            for table in tables:
                table_name = table[0]
                print(f"  ✅ {table_name}")
            
            # Проверяем структуру таблицы user_words
            if any(t[0] == 'user_words' for t in tables):
                print("\n📊 Структура таблицы user_words:")
                result = await session.execute(text("PRAGMA table_info(user_words);"))
                columns = result.fetchall()
                
                has_correct_answers = False
                for column in columns:
                    col_id, col_name, col_type, not_null, default_val, pk = column
                    print(f"  • {col_name} ({col_type})")
                    if col_name == 'correct_answers_count':
                        has_correct_answers = True
                
                if has_correct_answers:
                    print("\n✅ Поле 'correct_answers_count' присутствует!")
                else:
                    print("\n❌ Поле 'correct_answers_count' отсутствует!")
                    return False
            
        print("\n🎉 База данных успешно пересоздана с новой структурой!")
        print("📚 Теперь слова будут считаться выученными после:")
        print("   • Прохождения всех 7 интервалов повторения ИЛИ")
        print("   • 10 правильных ответов в тренировках")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при пересоздании базы данных: {e}")
        return False

async def main():
    success = await recreate_database()
    if success:
        print("\n🚀 База данных готова к использованию!")
        print("📝 Теперь можете запустить бота: python main.py")
    else:
        print("\n❌ Не удалось пересоздать базу данных")

if __name__ == "__main__":
    asyncio.run(main()) 