import asyncio
import os
import sys
import sqlite3

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def analyze_database_structure():
    """Подробный анализ структуры базы данных"""
    
    print("🔍 ПОДРОБНЫЙ АНАЛИЗ СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("="*60)
    
    # Прямое подключение к SQLite для более детального анализа
    db_path = "../vocabulary_bot.db"
    
    try:
        # Используем прямое подключение к SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📋 1. СПИСОК ВСЕХ ТАБЛИЦ:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"  ✅ {table_name}")
            
            # Подсчитываем записи в каждой таблице
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`;")
            count = cursor.fetchone()[0]
            print(f"     📊 Записей: {count}")
            
            # Показываем структуру таблицы
            cursor.execute(f"PRAGMA table_info(`{table_name}`);")
            columns = cursor.fetchall()
            print(f"     🔧 Структура:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_marker = " 🔑" if pk else ""
                null_marker = " ⚠️NOT NULL" if not_null else ""
                default_marker = f" (по умолчанию: {default_val})" if default_val else ""
                print(f"        • {col_name}: {col_type}{pk_marker}{null_marker}{default_marker}")
            
            # Показываем примеры данных, если есть
            if count > 0 and count <= 1000:  # Только для небольших таблиц
                print(f"     📖 Примеры данных:")
                try:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3;")
                    rows = cursor.fetchall()
                    col_names = [description[0] for description in cursor.description]
                    
                    for i, row in enumerate(rows, 1):
                        print(f"        Запись {i}:")
                        for col_name, value in zip(col_names, row):
                            display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                            print(f"          {col_name}: {display_value}")
                except Exception as e:
                    print(f"        ❌ Ошибка при чтении данных: {e}")
            
            print()
        
        conn.close()
        
        print("\n" + "="*60)
        print("🔧 2. СРАВНЕНИЕ С ОЖИДАЕМОЙ СТРУКТУРОЙ:")
        
        # Ожидаемые структуры из моделей
        expected_structures = {
            'users': ['id', 'telegram_id', 'username', 'first_name', 'last_name', 'is_active', 'notifications_enabled', 'created_at'],
            'words': ['id', 'word', 'definition', 'explanation', 'morpheme_type', 'difficulty_level', 'puzzle_pattern', 'hidden_letters', 'created_at'],
            'user_words': ['id', 'user_id', 'word_id', 'mistakes_count', 'correct_answers_count', 'current_interval_index', 'next_repetition', 'is_learned', 'created_at', 'last_reviewed'],
            'training_sessions': ['id', 'user_id', 'session_type', 'words_total', 'words_correct', 'words_incorrect', 'started_at', 'completed_at'],
            'training_answers': ['id', 'session_id', 'word_id', 'user_answer', 'is_correct', 'answered_at']
        }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for table_name, expected_cols in expected_structures.items():
            print(f"\n📊 Таблица '{table_name}':")
            
            try:
                cursor.execute(f"PRAGMA table_info(`{table_name}`);")
                actual_columns = cursor.fetchall()
                actual_col_names = [col[1] for col in actual_columns]
                
                print(f"  Ожидаемые поля: {', '.join(expected_cols)}")
                print(f"  Фактические поля: {', '.join(actual_col_names)}")
                
                missing_cols = set(expected_cols) - set(actual_col_names)
                extra_cols = set(actual_col_names) - set(expected_cols)
                
                if missing_cols:
                    print(f"  ❌ Отсутствующие поля: {', '.join(missing_cols)}")
                
                if extra_cols:
                    print(f"  ➕ Дополнительные поля: {', '.join(extra_cols)}")
                
                if not missing_cols and not extra_cols:
                    print(f"  ✅ Структура соответствует ожидаемой")
                    
            except sqlite3.OperationalError as e:
                print(f"  ❌ Таблица не существует: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при анализе базы данных: {e}")
        return False
    
    print(f"\n" + "="*60)
    print("🎯 3. РЕКОМЕНДАЦИИ ПО МИГРАЦИИ:")
    print("Анализ завершен. Теперь создадим план миграции.")
    
    return True

if __name__ == "__main__":
    asyncio.run(analyze_database_structure()) 