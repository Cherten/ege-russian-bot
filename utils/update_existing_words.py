import asyncio
import os
import sys

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from database.database import get_session
from database.models import Word

async def update_existing_words():
    """Обновляет все существующие слова, устанавливая им тип морфемы 'roots' и добавляет базовые определения"""
    
    async for session in get_session():
        try:
            # Получаем все слова без определения или с пустым определением
            words_query = select(Word).where(
                (Word.definition == None) | (Word.definition == '') | (Word.definition == 'None')
            )
            words_result = await session.execute(words_query)
            words = words_result.scalars().all()
            
            print(f"🔍 Найдено слов для обновления: {len(words)}")
            
            if not words:
                print("ℹ️ Все слова уже имеют определения")
                return
            
            # Обновляем каждое слово
            updated_count = 0
            for word in words:
                # Устанавливаем базовое определение
                basic_definition = f"Словарное слово: {word.word}"
                
                # Обновляем слово
                update_query = update(Word).where(Word.id == word.id).values(
                    definition=basic_definition,
                    morpheme_type='roots',  # Устанавливаем тип морфемы "Корни"
                    explanation=''  # Пустое пояснение
                )
                await session.execute(update_query)
                updated_count += 1
                
                print(f"✅ Обновлено слово: {word.word} → {basic_definition}")
            
            await session.commit()
            print(f"\n🎉 Успешно обновлено {updated_count} слов(а)!")
            print("📝 Все слова теперь имеют:")
            print("   - Тип морфемы: Корни") 
            print("   - Базовое определение")
            print("   - Пустое пояснение")
            
        except Exception as e:
            print(f"❌ Ошибка при обновлении слов: {e}")
            await session.rollback()
            raise

async def show_words_stats():
    """Показывает статистику слов по типам морфем"""
    
    async for session in get_session():
        # Подсчитываем слова по типам
        roots_query = select(Word).where(Word.morpheme_type == 'roots')
        roots_result = await session.execute(roots_query)
        roots_count = len(roots_result.scalars().all())
        
        prefixes_query = select(Word).where(Word.morpheme_type == 'prefixes')
        prefixes_result = await session.execute(prefixes_query)
        prefixes_count = len(prefixes_result.scalars().all())
        
        endings_query = select(Word).where(Word.morpheme_type == 'endings')
        endings_result = await session.execute(endings_query)
        endings_count = len(endings_result.scalars().all())
        
        spelling_query = select(Word).where(Word.morpheme_type == 'spelling')
        spelling_result = await session.execute(spelling_query)
        spelling_count = len(spelling_result.scalars().all())
        
        print(f"\n📊 Статистика слов по типам морфем:")
        print(f"🌿 Корни: {roots_count} слов")
        print(f"🔤 Приставки: {prefixes_count} слов")
        print(f"🔚 Окончания: {endings_count} слов")
        print(f"✍️ Слитное, раздельное, дефисное написание: {spelling_count} слов")
        print(f"📚 Всего слов: {roots_count + prefixes_count + endings_count + spelling_count}")

async def main():
    print("🔄 Запуск обновления существующих слов...\n")
    
    # Показываем статистику до обновления
    print("📊 Статистика ДО обновления:")
    await show_words_stats()
    
    # Обновляем слова
    await update_existing_words()
    
    # Показываем статистику после обновления
    print("\n📊 Статистика ПОСЛЕ обновления:")
    await show_words_stats()

if __name__ == "__main__":
    asyncio.run(main()) 