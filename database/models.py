from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    experience_points = Column(Integer, default=0)  # Очки опыта
    level = Column(Integer, default=1)  # Текущий уровень (1-25)
    current_streak = Column(Integer, default=0)  # Текущий стрик дней подряд
    best_streak = Column(Integer, default=0)  # Лучший стрик за все время
    last_training_date = Column(Date)  # Дата последней завершенной тренировки
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user_words = relationship("UserWord", back_populates="user")
    training_sessions = relationship("TrainingSession", back_populates="user")

class Word(Base):
    __tablename__ = 'words'
    
    id = Column(Integer, primary_key=True)
    word = Column(String(255), nullable=False, unique=True)
    definition = Column(Text)
    explanation = Column(Text)  # Пояснение для различения омофонов
    morpheme_type = Column(String(50), nullable=False, default='roots')  # roots, prefixes, endings, spelling
    difficulty_level = Column(Integer, default=1)  # 1-5
    puzzle_pattern = Column(String(255), nullable=False)  # Шаблон с пропусками (например: "ап_льс_н")
    hidden_letters = Column(String(100), nullable=False)  # Скрытые буквы (например: "еи")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user_words = relationship("UserWord", back_populates="word")

class UserWord(Base):
    __tablename__ = 'user_words'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('words.id'), nullable=False)
    mistakes_count = Column(Integer, default=1)
    correct_answers_count = Column(Integer, default=0)  # Счетчик правильных ответов
    current_interval_index = Column(Integer, default=0)
    next_repetition = Column(DateTime, nullable=False)
    is_learned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_reviewed = Column(DateTime)
    
    # Связи
    user = relationship("User", back_populates="user_words")
    word = relationship("Word", back_populates="user_words")

class TrainingSession(Base):
    __tablename__ = 'training_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_type = Column(String(50))  # 'new_words', 'repetition'
    words_total = Column(Integer)
    words_correct = Column(Integer, default=0)
    words_incorrect = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Связи
    user = relationship("User", back_populates="training_sessions")
    answers = relationship("TrainingAnswer", back_populates="session")

class TrainingAnswer(Base):
    __tablename__ = 'training_answers'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('training_sessions.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('words.id'), nullable=False)
    user_answer = Column(String(255))
    is_correct = Column(Boolean)
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    session = relationship("TrainingSession", back_populates="answers")
    word = relationship("Word") 