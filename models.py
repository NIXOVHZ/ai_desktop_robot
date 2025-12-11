# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import os

# 创建基类
Base = declarative_base()

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = 'chat_messages'  # 数据库中的表名

    # 定义字段（列）
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)  # 对话会话ID，方便区分不同对话
    role = Column(String(50), nullable=False)  # 'user' 或 'assistant'
    content = Column(Text, nullable=False)  # 消息内容
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间

    def __repr__(self):
        return f"<ChatMessage(session_id='{self.session_id}', role='{self.role}')>"

# 注意：我们稍后会在 database.py 中创建引擎和初始化表