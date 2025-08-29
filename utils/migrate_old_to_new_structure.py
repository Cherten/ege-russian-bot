import asyncio
import os
import sys
import sqlite3
import shutil
from datetime import datetime

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def migrate_old_to_new_structure():
    """Миграция старой базы данных к новой структуре с сохранением всех данных"""
    
    print("🔄 МИГРАЦИЯ СТАРОЙ БАЗЫ К НОВОЙ СТРУКТУРЕ")
    print("="*60)
    
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
        
        # 2. Подсчитываем данные до миграции
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_before = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM words;")
        words_before = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words;")
        user_words_before = cursor.fetchone()[0]
        
        print(f"\n📊 Данные ДО миграции:")
        print(f"   👥 Пользователей: {users_before}")
        print(f"   📚 Слов: {words_before}")
        print(f"   🔗 Связей user_words: {user_words_before}")
        
        conn.close()
        
        # 3. Выполняем миграцию через SQLAlchemy
        async for session in get_session():
            print(f"\n🔧 Выполняю миграцию полей...")
            
            # 3.1. Добавляем отсутствующие поля в таблицу words
            print("   📝 Добавляю поле 'explanation' в таблицу words...")
            try:
                await session.execute(text("ALTER TABLE words ADD COLUMN explanation TEXT;"))
                print("   ✅ Поле 'explanation' добавлено")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("   ℹ️  Поле 'explanation' уже существует")
                else:
                    raise e
            
            print("   📝 Добавляю поле 'morpheme_type' в таблицу words...")
            try:
                await session.execute(text("ALTER TABLE words ADD COLUMN morpheme_type VARCHAR(50) NOT NULL DEFAULT 'roots';"))
                print("   ✅ Поле 'morpheme_type' добавлено")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("   ℹ️  Поле 'morpheme_type' уже существует")
                else:
                    raise e
            
            # 3.2. Добавляем поле correct_answers_count в таблицу user_words
            print("   📝 Добавляю поле 'correct_answers_count' в таблицу user_words...")
            try:
                await session.execute(text("ALTER TABLE user_words ADD COLUMN correct_answers_count INTEGER NOT NULL DEFAULT 0;"))
                print("   ✅ Поле 'correct_answers_count' добавлено")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("   ℹ️  Поле 'correct_answers_count' уже существует")
                else:
                    raise e
            
            # 3.3. Инициализируем значения по умолчанию
            print("   🔄 Инициализация значений по умолчанию...")
            
            # Для новых полей в words
            await session.execute(text("UPDATE words SET explanation = '' WHERE explanation IS NULL;"))
            await session.execute(text("UPDATE words SET morpheme_type = 'roots' WHERE morpheme_type IS NULL OR morpheme_type = '';"))
            
            # Для correct_answers_count - подсчитываем из истории правильных ответов
            print("   🧮 Подсчитываю правильные ответы из истории тренировок...")
            
            # Обновляем счетчик правильных ответов на основе истории
            query = """
            UPDATE user_words 
            SET correct_answers_count = (
                SELECT COUNT(*)
                FROM training_answers ta
                JOIN training_sessions ts ON ta.session_id = ts.id
                WHERE ts.user_id = user_words.user_id 
                AND ta.word_id = user_words.word_id 
                AND ta.is_correct = 1
            )
            WHERE correct_answers_count = 0;
            """
            await session.execute(text(query))
            
            # Помечаем как выученные слова, у которых уже >= 5 правильных ответов
            await session.execute(text("""
                UPDATE user_words 
                SET is_learned = 1 
                WHERE correct_answers_count >= 5 AND is_learned = 0;
            """))
            
            await session.commit()
            
        # 4. Проверяем результат
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_after = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM words;")
        words_after = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words;")
        user_words_after = cursor.fetchone()[0]
        
        # Подсчитываем статистику по новым полям
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count > 0;")
        words_with_progress = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count >= 10;")
        auto_learned_words = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE is_learned = 1;")
        total_learned_words = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 Данные ПОСЛЕ миграции:")
        print(f"   👥 Пользователей: {users_after} (было: {users_before})")
        print(f"   📚 Слов: {words_after} (было: {words_before})")
        print(f"   🔗 Связей user_words: {user_words_after} (было: {user_words_before})")
        print(f"\n📈 Новая статистика:")
        print(f"   🎯 Слов с прогрессом: {words_with_progress}")
        print(f"   🏆 Автоматически выученных (10+ ответов): {auto_learned_words}")
        print(f"   ✅ Всего выученных слов: {total_learned_words}")
        
        if users_after == users_before and words_after == words_before and user_words_after == user_words_before:
            print(f"\n🎉 МИГРАЦИЯ УСПЕШНА!")
            print(f"   ✅ Все данные сохранены")
            print(f"   ✅ Структура обновлена")
            print(f"   ✅ Новая функциональность активна")
            print(f"\n📚 Теперь слова будут считаться выученными после:")
            print(f"   • Прохождения всех 7 интервалов повторения ИЛИ")
            print(f"   • 5 правильных ответов в тренировках")
        else:
            print(f"\n❌ ПОТЕРЯ ДАННЫХ ОБНАРУЖЕНА!")
            print(f"Восстанавливаю из резервной копии...")
            shutil.copy2(backup_path, db_path)
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        
        # Восстанавливаем из резервной копии
        if os.path.exists(backup_path):
            print("🔄 Восстанавливаем из резервной копии...")
            shutil.copy2(backup_path, db_path)
            print("✅ База данных восстановлена из резервной копии")
        
        return False

async def main():
    print("🛡️  БЕЗОПАСНАЯ МИГРАЦИЯ СТАРОЙ БАЗЫ")
    print("Эта миграция обновит структуру старой базы данных:")
    print("• Добавит отсутствующие поля")  
    print("• Подсчитает правильные ответы из истории")
    print("• Пометит слова как выученные при достижении 5+ правильных ответов")
    print("• Сохранит все существующие данные")
    print("="*60)
    
    success = await migrate_old_to_new_structure()
    
    if success:
        print("\n🚀 Миграция завершена успешно!")
        print("📝 База данных готова к работе с ботом!")
        print("💡 Теперь можете запустить: python main.py")
    else:
        print("\n❌ Миграция не выполнена")

if __name__ == "__main__":
    asyncio.run(main()) 