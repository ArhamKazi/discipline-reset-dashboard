from sqlalchemy import Column, Integer, Boolean, Float, Date
from database import Base
from sqlalchemy import String
from sqlalchemy import String

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class DailyLog(Base):
    __tablename__="daily_logs"

    id=Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True)
    wake_on_time=Column(Boolean, default=False)
    sleep_on_time=Column(Boolean, default=False)
    gym= Column(Boolean, default=False)
    applications_done= Column(Integer, default=0)
    learning_minutes=Column(Integer, default=0)
    gaming_violation=Column(Boolean, default=False)
    salah_count=Column(Integer, default=0)
    weight=Column(Float, nullable=True)
