#!/usr/bin/env python3
"""
Миграция для добавления полей стрика в таблицу users
"""

import sqlite3
import os
from datetime import datetime

def add_streak_fields():
    """Добавляет поля для отслеживания стриков в таблицу users"""
    db_path = "vocabulary_bot.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return False
    
    print("🔄 Добавляем поля для отслеживания стриков...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем существующие столбцы
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Существующие столбцы: {existing_columns}")
        
        # Добавляем новые столбцы, если их еще нет
        fields_to_add = [
            ("current_streak", "INTEGER DEFAULT 0"),
            ("best_streak", "INTEGER DEFAULT 0"), 
            ("last_training_date", "DATE")
        ]
        
        for field_name, field_definition in fields_to_add:
            if field_name not in existing_columns:
                print(f"➕ Добавляем поле {field_name}...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_definition}")
                print(f"✅ Поле {field_name} добавлено успешно!")
            else:
                print(f"⚠️ Поле {field_name} уже существует, пропускаем...")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(users)")
        all_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Все столбцы после миграции: {all_columns}")
        
        conn.close()
        
        print("✅ Миграция полей стрика завершена успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении полей стрика: {e}")
        return False

if __name__ == "__main__":
    success = add_streak_fields()
    if success:
        print("\n🎉 Поля для отслеживания стриков добавлены!")
        print("📊 Теперь система может отслеживать:")
        print("   • current_streak - текущий стрик дней подряд")
        print("   • best_streak - лучший стрик за все время") 
        print("   • last_training_date - дата последней тренировки")
    else:
        print("\n💥 Миграция завершилась с ошибками!")
