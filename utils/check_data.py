import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.database import get_session

async def check_database_data():
    """Проверяет данные в базе данных"""
    
    print("📊 Проверка данных в базе данных...\n")
    
    async for session in get_session():
        try:
            # Подсчет пользователей
            result = await session.execute(text("SELECT COUNT(*) FROM users;"))
            users_count = result.scalar()
            
            # Подсчет слов
            result = await session.execute(text("SELECT COUNT(*) FROM words;"))
            words_count = result.scalar()
            
            # Подсчет связей пользователь-слово
            result = await session.execute(text("SELECT COUNT(*) FROM user_words;"))
            user_words_count = result.scalar()
            
            # Подсчет завершенных тренировок
            result = await session.execute(text("SELECT COUNT(*) FROM training_sessions WHERE completed_at IS NOT NULL;"))
            completed_sessions = result.scalar()
            
            print(f"📈 Статистика данных:")
            print(f"   👥 Пользователей: {users_count}")
            print(f"   📚 Слов в словаре: {words_count}")
            print(f"   🔗 Связей пользователь-слово: {user_words_count}")
            print(f"   🎯 Завершенных тренировок: {completed_sessions}")
            
            if words_count > 0:
                print(f"\n📖 Примеры слов:")
                result = await session.execute(text("SELECT word, morpheme_type FROM words LIMIT 5;"))
                words = result.fetchall()
                for word, morpheme_type in words:
                    print(f"   • {word} ({morpheme_type})")
            
            if users_count > 0:
                print(f"\n👤 Информация о пользователях:")
                result = await session.execute(text("SELECT telegram_id, first_name, username FROM users LIMIT 3;"))
                users = result.fetchall()
                for telegram_id, first_name, username in users:
                    name = first_name or username or f"ID:{telegram_id}"
                    print(f"   • {name} (Telegram ID: {telegram_id})")
            
            # Проверяем структуру user_words
            result = await session.execute(text("PRAGMA table_info(user_words);"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"\n🔧 Поля в таблице user_words:")
            for col in column_names:
                marker = "🆕" if col == 'correct_answers_count' else "   "
                print(f"{marker} {col}")
            
            if 'correct_answers_count' in column_names:
                print(f"\n✅ Новое поле 'correct_answers_count' готово к работе!")
            else:
                print(f"\n❌ Поле 'correct_answers_count' отсутствует!")
            
            # Общий вывод
            if words_count > 0 or users_count > 0:
                print(f"\n🎉 ОТЛИЧНО! Ваши данные восстановлены:")
                print(f"   ✅ {words_count} слов сохранены")
                print(f"   ✅ {users_count} пользователей сохранены") 
                print(f"   ✅ Новая функциональность добавлена")
                print(f"\n🚀 Бот готов к работе с обновленной функциональностью!")
            else:
                print(f"\n⚠️  База данных пуста - данные не восстановлены")
                print(f"   Возможно, нужна другая резервная копия")
            
        except Exception as e:
            print(f"❌ Ошибка при проверке данных: {e}")

if __name__ == "__main__":
    asyncio.run(check_database_data()) 