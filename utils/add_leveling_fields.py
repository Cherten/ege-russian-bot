#!/usr/bin/env python3
"""
Скрипт миграции для добавления полей системы уровней в таблицу users
Добавляет поля: experience_points (INTEGER) и level (INTEGER)
"""

import asyncio
import sys
import os

# Добавляем путь к проекту для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import engine

async def add_leveling_fields():
    """Добавляет поля для системы уровней в таблицу users"""
    print("🔄 Добавление полей системы уровней в таблицу users...")
    
    try:
        async with engine.begin() as conn:
            # Проверяем, существуют ли поля уже (SQLite синтаксис)
            check_columns_query = text("""
                PRAGMA table_info(users)
            """)
            
            result = await conn.execute(check_columns_query)
            existing_columns = {row[1] for row in result.fetchall()}
            
            # Добавляем поле experience_points, если его нет
            if 'experience_points' not in existing_columns:
                add_experience_query = text("""
                    ALTER TABLE users 
                    ADD COLUMN experience_points INTEGER DEFAULT 0
                """)
                await conn.execute(add_experience_query)
                print("✅ Добавлено поле experience_points")
            else:
                print("ℹ️  Поле experience_points уже существует")
            
            # Добавляем поле level, если его нет
            if 'level' not in existing_columns:
                add_level_query = text("""
                    ALTER TABLE users 
                    ADD COLUMN level INTEGER DEFAULT 1
                """)
                await conn.execute(add_level_query)
                print("✅ Добавлено поле level")
            else:
                print("ℹ️  Поле level уже существует")
            
            # Обновляем существующих пользователей, у которых level = NULL или 0
            update_users_query = text("""
                UPDATE users 
                SET level = 1, experience_points = 0 
                WHERE level IS NULL OR level = 0 OR experience_points IS NULL
            """)
            result = await conn.execute(update_users_query)
            updated_count = result.rowcount
            
            if updated_count > 0:
                print(f"✅ Обновлено {updated_count} пользователей с базовыми значениями")
            
        print("🎉 Миграция успешно завершена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False

async def rollback_leveling_fields():
    """Откатывает изменения (удаляет поля уровней)"""
    print("🔄 Откат миграции - удаление полей системы уровней...")
    
    try:
        async with engine.begin() as conn:
            # Удаляем поле experience_points
            try:
                drop_experience_query = text("""
                    ALTER TABLE users DROP COLUMN experience_points
                """)
                await conn.execute(drop_experience_query)
                print("✅ Удалено поле experience_points")
            except Exception as e:
                print(f"ℹ️  Поле experience_points не найдено или уже удалено: {e}")
            
            # Удаляем поле level
            try:
                drop_level_query = text("""
                    ALTER TABLE users DROP COLUMN level
                """)
                await conn.execute(drop_level_query)
                print("✅ Удалено поле level")
            except Exception as e:
                print(f"ℹ️  Поле level не найдено или уже удалено: {e}")
        
        print("🎉 Откат миграции успешно завершен!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при откате миграции: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        asyncio.run(rollback_leveling_fields())
    else:
        print("🎯 Миграция базы данных для системы уровней")
        print("Использование:")
        print("  python add_leveling_fields.py          - добавить поля")
        print("  python add_leveling_fields.py --rollback - откатить изменения")
        print()
        
        if input("Продолжить миграцию? (y/N): ").lower() == 'y':
            success = asyncio.run(add_leveling_fields())
            if success:
                print("\n🎉 Система уровней готова к использованию!")
            else:
                print("\n❌ Миграция не выполнена из-за ошибок.")
                sys.exit(1)
        else:
            print("Миграция отменена пользователем.")
