import sqlite3
import sys
import os

def migrate_old_database(db_path):
    """Миграция старой базы данных к новой структуре"""
    
    print(f"🔄 Начинаем миграцию базы данных: {db_path}")
    
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем текущую структуру таблицы words
        cursor.execute("PRAGMA table_info(words)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Текущие колонки в таблице words: {columns}")
        
        # Добавляем колонку explanation, если её нет
        if 'explanation' not in columns:
            print("➕ Добавляем колонку 'explanation'...")
            cursor.execute("ALTER TABLE words ADD COLUMN explanation TEXT DEFAULT ''")
            print("✅ Колонка 'explanation' добавлена")
        else:
            print("ℹ️ Колонка 'explanation' уже существует")
        
        # Добавляем колонку morpheme_type, если её нет
        if 'morpheme_type' not in columns:
            print("➕ Добавляем колонку 'morpheme_type'...")
            cursor.execute("ALTER TABLE words ADD COLUMN morpheme_type TEXT DEFAULT 'roots'")
            print("✅ Колонка 'morpheme_type' добавлена")
        else:
            print("ℹ️ Колонка 'morpheme_type' уже существует")
        
        # Устанавливаем всем словам тип "roots" (Корни)
        print("🌿 Устанавливаем всем словам тип морфемы 'roots'...")
        cursor.execute("UPDATE words SET morpheme_type = 'roots' WHERE morpheme_type IS NULL OR morpheme_type = ''")
        updated_rows = cursor.rowcount
        print(f"✅ Обновлено {updated_rows} слов")
        
        # Устанавливаем пустые пояснения, если они NULL
        print("📝 Устанавливаем пустые пояснения...")
        cursor.execute("UPDATE words SET explanation = '' WHERE explanation IS NULL")
        updated_explanations = cursor.rowcount
        print(f"✅ Обновлено {updated_explanations} пояснений")
        
        # Проверяем количество слов
        cursor.execute("SELECT COUNT(*) FROM words")
        total_words = cursor.fetchone()[0]
        
        # Проверяем распределение по типам морфем
        cursor.execute("SELECT morpheme_type, COUNT(*) FROM words GROUP BY morpheme_type")
        morpheme_stats = cursor.fetchall()
        
        print("\n📊 Статистика после миграции:")
        print(f"📚 Всего слов: {total_words}")
        print("🔤 Распределение по типам морфем:")
        for morpheme_type, count in morpheme_stats:
            morpheme_name = {
                'roots': '🌿 Корни',
                'prefixes': '🔤 Приставки',
                'endings': '🔚 Окончания',
                'spelling': '✍️ Правописание'
            }.get(morpheme_type, morpheme_type)
            print(f"   - {morpheme_name}: {count} слов")
        
        # Сохраняем изменения
        conn.commit()
        print("\n✅ Миграция успешно завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True

def main():
    """Главная функция"""
    
    # Путь к базе данных
    db_path = "vocabulary_bot.db"
    
    # Проверяем существование файла
    if not os.path.exists(db_path):
        print(f"❌ Файл базы данных не найден: {db_path}")
        print("Убедитесь, что вы запускаете скрипт в папке с файлом vocabulary_bot.db")
        sys.exit(1)
    
    # Подтверждение от пользователя
    print("⚠️  ВНИМАНИЕ: Этот скрипт изменит структуру базы данных!")
    print("Убедитесь, что вы создали резервную копию!")
    print(f"📁 Будет обработан файл: {os.path.abspath(db_path)}")
    
    response = input("\nПродолжить миграцию? (да/нет): ").lower()
    if response not in ['да', 'yes', 'y', 'д']:
        print("❌ Миграция отменена")
        sys.exit(0)
    
    # Выполняем миграцию
    success = migrate_old_database(db_path)
    
    if success:
        print("\n🎉 Миграция завершена успешно!")
        print("Теперь можно использовать новую версию бота с этой базой данных.")
        print("\n📋 Следующие шаги:")
        print("1. Запустите бота: python main.py")
        print("2. Проверьте статистику: /admin → 📊 Статистика")
        print("3. Все слова должны быть в разделе '🌿 Корни'")
    else:
        print("\n💥 Миграция не удалась!")
        print("Восстановите базу данных из резервной копии и попробуйте снова.")

if __name__ == "__main__":
    main() 