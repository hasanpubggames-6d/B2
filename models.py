from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    full_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    daily_limit = Column(Integer, default=10)
    used_today = Column(Integer, default=0)
    last_use = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(255))
    invite_link = Column(String(255))
    is_active = Column(Boolean, default=True)

class Translation(Base):
    __tablename__ = 'translations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    original_text = Column(Text)
    translated_text = Column(Text)
    source_lang = Column(String(50))
    target_lang = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class ImageLog(Base):
    __tablename__ = 'image_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    file_id = Column(String(255))
    ocr_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIToken(Base):
    __tablename__ = 'api_tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    token = Column(String(255), unique=True)
    usage_limit = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(255), primary_key=True)
    value = Column(Text)

class ErrorLog(Base):
    __tablename__ = 'error_logs'
    id = Column(Integer, primary_key=True)
    error_message = Column(Text)
    stack_trace = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
