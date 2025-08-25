import os
import sys
import sqlite3
import shutil
from datetime import datetime

def step_by_step_migration():
    """Пошаговая миграция базы данных"""
    
    print("🔄 ПОШАГОВАЯ МИГРАЦИЯ БАЗЫ ДАННЫХ")
    print("="*50)
    
    db_path = "../vocabulary_bot.db"
    backup_path = f"../vocabulary_bot_backup_step_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        # Создаем резервную копию
        shutil.copy2(db_path, backup_path)
        print(f"✅ Резервная копия: {os.path.basename(backup_path)}")
        
        # Работаем напрямую с SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📊 ШАГ 1: Проверка текущей структуры")
        
        # Проверяем user_words
        cursor.execute("PRAGMA table_info(user_words);")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Поля в user_words: {', '.join(column_names)}")
        
        # Проверяем words
        cursor.execute("PRAGMA table_info(words);")
        word_columns = cursor.fetchall()
        word_column_names = [col[1] for col in word_columns]
        
        print(f"Поля в words: {', '.join(word_column_names)}")
        
        # ШАГ 2: Добавляем отсутствующие поля
        print(f"\n🔧 ШАГ 2: Добавление отсутствующих полей")
        
        # Добавляем explanation в words если нет
        if 'explanation' not in word_column_names:
            print("   📝 Добавляю поле 'explanation' в words...")
            cursor.execute("ALTER TABLE words ADD COLUMN explanation TEXT;")
            conn.commit()
            print("   ✅ Добавлено!")
        else:
            print("   ℹ️  Поле 'explanation' уже есть")
        
        # Добавляем morpheme_type в words если нет
        if 'morpheme_type' not in word_column_names:
            print("   📝 Добавляю поле 'morpheme_type' в words...")
            cursor.execute("ALTER TABLE words ADD COLUMN morpheme_type VARCHAR(50) DEFAULT 'roots';")
            conn.commit()
            print("   ✅ Добавлено!")
        else:
            print("   ℹ️  Поле 'morpheme_type' уже есть")
        
        # Добавляем correct_answers_count в user_words если нет
        if 'correct_answers_count' not in column_names:
            print("   📝 Добавляю поле 'correct_answers_count' в user_words...")
            cursor.execute("ALTER TABLE user_words ADD COLUMN correct_answers_count INTEGER DEFAULT 0;")
            conn.commit()
            print("   ✅ Добавлено!")
            
            # Обновляем структуру после добавления
            cursor.execute("PRAGMA table_info(user_words);")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
        else:
            print("   ℹ️  Поле 'correct_answers_count' уже есть")
        
        print(f"\n📈 ШАГ 3: Инициализация значений по умолчанию")
        
        # Заполняем пустые значения в words
        cursor.execute("UPDATE words SET explanation = '' WHERE explanation IS NULL;")
        cursor.execute("UPDATE words SET morpheme_type = 'roots' WHERE morpheme_type IS NULL OR morpheme_type = '';")
        
        # Инициализируем correct_answers_count нулями
        cursor.execute("UPDATE user_words SET correct_answers_count = 0 WHERE correct_answers_count IS NULL;")
        
        conn.commit()
        print("   ✅ Значения по умолчанию установлены")
        
        print(f"\n🧮 ШАГ 4: Подсчет правильных ответов из истории")
        
        # Подсчитываем правильные ответы для каждой связи user-word
        cursor.execute("""
            UPDATE user_words 
            SET correct_answers_count = (
                SELECT COUNT(*)
                FROM training_answers ta
                JOIN training_sessions ts ON ta.session_id = ts.id
                WHERE ts.user_id = user_words.user_id 
                AND ta.word_id = user_words.word_id 
                AND ta.is_correct = 1
            );
        """)
        
        conn.commit()
        print("   ✅ Правильные ответы подсчитаны из истории")
        
        print(f"\n🏆 ШАГ 5: Автоматическое помечение выученных слов")
        
        # Помечаем слова с 10+ правильными ответами как выученные
        cursor.execute("""
            UPDATE user_words 
            SET is_learned = 1 
            WHERE correct_answers_count >= 10 AND is_learned = 0;
        """)
        
        updated_rows = cursor.rowcount
        conn.commit()
        print(f"   ✅ {updated_rows} слов помечены как выученные (10+ правильных ответов)")
        
        # ШАГ 6: Финальная проверка
        print(f"\n📊 ШАГ 6: Финальная проверка")
        
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM words;")
        words_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words;")
        user_words_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count > 0;")
        words_with_answers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count >= 10;")
        auto_learned = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words WHERE is_learned = 1;")
        total_learned = cursor.fetchone()[0]
        
        # Показываем примеры
        cursor.execute("SELECT correct_answers_count, COUNT(*) FROM user_words GROUP BY correct_answers_count ORDER BY correct_answers_count;")
        distribution = cursor.fetchall()
        
        print(f"   👥 Пользователей: {users_count}")
        print(f"   📚 Слов: {words_count}")
        print(f"   🔗 Связей user_words: {user_words_count}")
        print(f"   🎯 Слов с правильными ответами: {words_with_answers}")
        print(f"   🏆 Автоматически выученных (10+): {auto_learned}")
        print(f"   ✅ Всего выученных: {total_learned}")
        
        print(f"\n📈 Распределение по количеству правильных ответов:")
        for count, num in distribution:
            if count <= 15:  # Показываем только первые 15
                print(f"   {count} правильных ответов: {num} слов")
        
        conn.close()
        
        print(f"\n🎉 МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print(f"✅ Все данные сохранены")
        print(f"✅ Структура обновлена") 
        print(f"✅ Новая функциональность активна")
        
        print(f"\n📚 Теперь слова считаются выученными после:")
        print(f"   • Прохождения всех 7 интервалов повторения ИЛИ")
        print(f"   • 10 правильных ответов в тренировках")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        # Восстанавливаем копию
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            print("🔄 База восстановлена из копии")
        return False

if __name__ == "__main__":
    step_by_step_migration() 