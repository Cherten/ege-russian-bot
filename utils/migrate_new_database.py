#!/usr/bin/env python3
"""
Полная миграция новой базы данных для совместимости с текущей версией бота
"""

import sqlite3
import os
from datetime import datetime

def migrate_new_database():
    """Применяет все необходимые миграции к новой базе данных"""
    db_path = "vocabulary_bot.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных vocabulary_bot.db не найдена!")
        return False
    
    print("🔄 ПОЛНАЯ МИГРАЦИЯ НОВОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Создаем бэкап перед миграцией
    backup_path = f"vocabulary_bot_backup_before_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        # Создаем backup
        print(f"💾 Создаем бэкап: {backup_path}")
        
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Бэкап создан успешно!")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем текущую структуру
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Существующие столбцы: {existing_columns}")
        
        # Список всех полей, которые должны быть в новой версии
        required_fields = [
            ("experience_points", "INTEGER DEFAULT 0"),
            ("level", "INTEGER DEFAULT 1"), 
            ("current_streak", "INTEGER DEFAULT 0"),
            ("best_streak", "INTEGER DEFAULT 0"),
            ("last_training_date", "DATE")
        ]
        
        # Добавляем отсутствующие поля
        for field_name, field_definition in required_fields:
            if field_name not in existing_columns:
                print(f"➕ Добавляем поле {field_name}...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_definition}")
                print(f"✅ Поле {field_name} добавлено успешно!")
            else:
                print(f"⚠️ Поле {field_name} уже существует, пропускаем...")
        
        # Проверяем структуру таблицы user_words (для правильного подсчета выученных слов)
        cursor.execute("PRAGMA table_info(user_words)")
        user_words_columns = [column[1] for column in cursor.fetchall()]
        
        if 'correct_answers_count' not in user_words_columns:
            print(f"➕ Добавляем поле correct_answers_count в таблицу user_words...")
            cursor.execute("ALTER TABLE user_words ADD COLUMN correct_answers_count INTEGER DEFAULT 0")
            print(f"✅ Поле correct_answers_count добавлено!")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(users)")
        all_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Все столбцы после миграции: {all_columns}")
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM words")
        words_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users") 
        users_count = cursor.fetchone()[0]
        
        print(f"\n📊 СТАТИСТИКА ПОСЛЕ МИГРАЦИИ:")
        print(f"   📚 Слов в БД: {words_count}")
        print(f"   👥 Пользователей в БД: {users_count}")
        
        conn.close()
        
        print(f"\n✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print(f"🎯 Теперь база данных совместима с новой версией бота!")
        print(f"💾 Бэкап сохранен как: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        
        # Пытаемся восстановить из backup в случае ошибки
        if os.path.exists(backup_path):
            print(f"🔄 Попытка восстановления из бэкапа...")
            try:
                shutil.copy2(backup_path, db_path)
                print(f"✅ База данных восстановлена из бэкапа")
            except:
                print(f"❌ Не удалось восстановить из бэкапа")
                
        return False

if __name__ == "__main__":
    success = migrate_new_database()
    if success:
        print("\n🎉 База данных готова к работе с новой версией бота!")
        print("🚀 Можете запускать бота: python main.py")
    else:
        print("\n💥 Миграция завершилась с ошибками!")
