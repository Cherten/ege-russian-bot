import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def check_database_structure():
    """Проверяет структуру базы данных и выводит информацию о таблицах"""
    
    async for session in get_session():
        try:
            print("🔍 Проверка структуры базы данных...\n")
            
            # Получаем список всех таблиц
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            
            if not tables:
                print("❌ База данных пуста - таблиц не найдено!")
                return False
            
            print("📋 Найденные таблицы:")
            table_names = []
            for table in tables:
                table_name = table[0]
                table_names.append(table_name)
                print(f"  ✅ {table_name}")
            
            print()
            
            # Проверяем наличие нужных таблиц
            required_tables = ['users', 'words', 'user_words', 'training_sessions', 'training_answers']
            missing_tables = []
            
            for required_table in required_tables:
                if required_table not in table_names:
                    missing_tables.append(required_table)
            
            if missing_tables:
                print("❌ Отсутствующие таблицы:")
                for missing in missing_tables:
                    print(f"  ❌ {missing}")
                return False
            else:
                print("✅ Все необходимые таблицы присутствуют!")
            
            print("\n" + "="*50)
            
            # Проверяем структуру таблицы user_words
            if 'user_words' in table_names:
                print("📊 Структура таблицы user_words:")
                result = await session.execute(text("PRAGMA table_info(user_words);"))
                columns = result.fetchall()
                
                for column in columns:
                    col_id, col_name, col_type, not_null, default_val, pk = column
                    print(f"  • {col_name} ({col_type}) {'NOT NULL' if not_null else 'NULL'} {'PK' if pk else ''}")
                
                # Проверяем есть ли уже поле correct_answers_count
                column_names = [col[1] for col in columns]
                if 'correct_answers_count' in column_names:
                    print("\n✅ Поле 'correct_answers_count' уже существует!")
                else:
                    print("\n⚠️  Поле 'correct_answers_count' отсутствует - нужна миграция")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке базы данных: {e}")
            return False

async def main():
    success = await check_database_structure()
    if not success:
        print("\n🔧 Возможно, нужно создать таблицы. Попробуйте запустить:")
        print("python -c \"from database.database import init_db; import asyncio; asyncio.run(init_db())\"")

if __name__ == "__main__":
    asyncio.run(main()) 