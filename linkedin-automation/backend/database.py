from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class PostHistory(Base):
    __tablename__ = 'post_history'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(100))
    content = Column(Text)
    image_url = Column(String(500))
    linkedin_url = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    engagement_count = Column(Integer, default=0)
    source_type = Column(String(50))  # 'mac_notes', 'google_docs', 'plain_text'

class CommentHistory(Base):
    __tablename__ = 'comment_history'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(100))
    commenter_name = Column(String(200))
    comment_text = Column(Text)
    reply_sent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class MessageHistory(Base):
    __tablename__ = 'message_history'
    
    id = Column(Integer, primary_key=True)
    recipient_profile = Column(String(200))
    message_text = Column(Text)
    context = Column(String(100))  # 'post_like', 'comment', 'connection'
    sent_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(engine)

