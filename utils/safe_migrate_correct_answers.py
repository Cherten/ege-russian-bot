import asyncio
import os
import sys
import shutil
from datetime import datetime

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def safe_migrate_correct_answers_count():
    """Безопасная миграция: добавляет поле correct_answers_count с сохранением всех данных"""
    
    print("🔄 Безопасная миграция для добавления счетчика правильных ответов...\n")
    
    db_path = "../vocabulary_bot.db"
    backup_path = f"../vocabulary_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        # 1. Создаем резервную копию
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✅ Создана резервная копия: {os.path.basename(backup_path)}")
        else:
            print("❌ Файл базы данных не найден!")
            return False
        
        async for session in get_session():
            # 2. Проверяем существующие таблицы
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            table_names = [t[0] for t in tables]
            
            print("📋 Найденные таблицы:")
            for table in table_names:
                print(f"  ✅ {table}")
            
            if 'user_words' not in table_names:
                print("❌ Таблица user_words не найдена!")
                return False
            
            # 3. Проверяем структуру таблицы user_words
            result = await session.execute(text("PRAGMA table_info(user_words);"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'correct_answers_count' in column_names:
                print("✅ Поле 'correct_answers_count' уже существует!")
                return True
            
            print("📊 Текущая структура таблицы user_words:")
            for column in columns:
                col_id, col_name, col_type, not_null, default_val, pk = column
                print(f"  • {col_name} ({col_type})")
            
            # 4. Подсчитываем существующие данные перед миграцией
            result = await session.execute(text("SELECT COUNT(*) FROM user_words;"))
            user_words_count = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM users;"))
            users_count = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM words;"))
            words_count = result.scalar()
            
            print(f"\n📊 Существующие данные:")
            print(f"   👥 Пользователей: {users_count}")
            print(f"   📚 Слов: {words_count}")
            print(f"   🔗 Связей пользователь-слово: {user_words_count}")
            
            # 5. Добавляем новое поле
            print("\n🔧 Добавляем поле 'correct_answers_count'...")
            await session.execute(text(
                "ALTER TABLE user_words ADD COLUMN correct_answers_count INTEGER NOT NULL DEFAULT 0;"
            ))
            
            # 6. Инициализируем значения для существующих записей
            print("🔄 Инициализация значений для существующих записей...")
            await session.execute(text(
                "UPDATE user_words SET correct_answers_count = 0 WHERE correct_answers_count IS NULL;"
            ))
            
            await session.commit()
            
            # 7. Проверяем результат
            result = await session.execute(text("PRAGMA table_info(user_words);"))
            new_columns = result.fetchall()
            
            print("\n📊 Обновленная структура таблицы user_words:")
            for column in new_columns:
                col_id, col_name, col_type, not_null, default_val, pk = column
                marker = "🆕" if col_name == 'correct_answers_count' else "  "
                print(f"{marker} • {col_name} ({col_type})")
            
            # 8. Проверяем, что данные сохранились
            result = await session.execute(text("SELECT COUNT(*) FROM user_words;"))
            final_count = result.scalar()
            
            if final_count == user_words_count:
                print(f"\n✅ Все данные сохранены! ({final_count} записей)")
            else:
                print(f"\n❌ Потеря данных! Было: {user_words_count}, стало: {final_count}")
                return False
        
        print(f"\n🎉 Миграция успешно выполнена!")
        print(f"📚 Теперь слова будут считаться выученными после:")
        print(f"   • Прохождения всех 7 интервалов повторения ИЛИ")
        print(f"   • 10 правильных ответов в тренировках")
        print(f"\n💾 Резервная копия сохранена: {os.path.basename(backup_path)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        
        # Восстанавливаем из резервной копии в случае ошибки
        if os.path.exists(backup_path):
            print("🔄 Восстанавливаем из резервной копии...")
            shutil.copy2(backup_path, db_path)
            print("✅ База данных восстановлена из резервной копии")
        
        return False

async def main():
    print("🛡️  БЕЗОПАСНАЯ МИГРАЦИЯ")
    print("Эта миграция:")
    print("• Создает резервную копию перед изменениями")
    print("• Сохраняет все существующие данные")
    print("• Восстанавливает из копии при ошибке")
    print("="*50)
    
    success = await safe_migrate_correct_answers_count()
    
    if success:
        print("\n🚀 Миграция завершена успешно!")
        print("📝 Теперь можете запустить бота: python main.py")
    else:
        print("\n❌ Миграция не выполнена")

if __name__ == "__main__":
    asyncio.run(main()) 