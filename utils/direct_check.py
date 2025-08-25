import sqlite3

def direct_database_check():
    """Прямая проверка данных через SQLite"""
    
    print("🔍 ПРЯМАЯ ПРОВЕРКА БАЗЫ ДАННЫХ")
    print("="*40)
    
    db_path = "../vocabulary_bot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Подсчет записей
        cursor.execute("SELECT COUNT(*) FROM users;")
        users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM words;")
        words = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_words;")
        user_words = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM training_sessions WHERE completed_at IS NOT NULL;")
        sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM training_answers;")
        answers = cursor.fetchone()[0]
        
        print(f"📊 СТАТИСТИКА ДАННЫХ:")
        print(f"   👥 Пользователей: {users}")
        print(f"   📚 Слов: {words}")
        print(f"   🔗 Связей user_words: {user_words}")
        print(f"   🎯 Завершенных тренировок: {sessions}")
        print(f"   📝 Ответов в тренировках: {answers}")
        
        if words > 0:
            print(f"\n📖 ПРИМЕРЫ СЛОВ:")
            cursor.execute("SELECT word, morpheme_type, explanation FROM words LIMIT 5;")
            sample_words = cursor.fetchall()
            for word, morph_type, explanation in sample_words:
                exp_text = f" ({explanation})" if explanation else ""
                print(f"   • {word} [{morph_type}]{exp_text}")
        
        if user_words > 0:
            print(f"\n🎯 СТАТИСТИКА ПО ПРАВИЛЬНЫМ ОТВЕТАМ:")
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count > 0;")
            with_answers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE correct_answers_count >= 10;")
            auto_learned = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE is_learned = 1;")
            total_learned = cursor.fetchone()[0]
            
            print(f"   🎯 Слов с правильными ответами: {with_answers}")
            print(f"   🏆 Автоматически выученных (10+ ответов): {auto_learned}")
            print(f"   ✅ Всего выученных слов: {total_learned}")
            
            # Топ слов по правильным ответам
            cursor.execute("""
                SELECT w.word, uw.correct_answers_count, uw.is_learned
                FROM user_words uw 
                JOIN words w ON uw.word_id = w.id 
                WHERE uw.correct_answers_count > 0 
                ORDER BY uw.correct_answers_count DESC 
                LIMIT 10;
            """)
            top_words = cursor.fetchall()
            
            if top_words:
                print(f"\n🏆 ТОП СЛОВ ПО ПРАВИЛЬНЫМ ОТВЕТАМ:")
                for word, count, learned in top_words:
                    learned_mark = "✅" if learned else "📚"
                    print(f"   {learned_mark} {word}: {count} правильных ответов")
        
        # Проверка структуры user_words
        print(f"\n🔧 СТРУКТУРА ТАБЛИЦЫ USER_WORDS:")
        cursor.execute("PRAGMA table_info(user_words);")
        columns = cursor.fetchall()
        
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            marker = "🆕" if col_name == 'correct_answers_count' else "   "
            print(f"{marker} {col_name} ({col_type})")
        
        conn.close()
        
        print(f"\n🎉 ИТОГ:")
        if words > 0 and user_words > 0:
            print(f"✅ База данных содержит все данные!")
            print(f"✅ Новое поле 'correct_answers_count' добавлено!")
            print(f"✅ Структура готова для работы с ботом!")
            print(f"\n🚀 Можно запускать бота: python main.py")
        else:
            print(f"❌ База данных пуста или повреждена")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

if __name__ == "__main__":
    direct_database_check() 