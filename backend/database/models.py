from sqlalchemy import BigInteger, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class WebAccount(Base):
    __tablename__ = 'web_accounts'
    id = Column(Integer, primary_key=True)
    subject = Column(String, unique=True, nullable=False)

class LoginAccount(Base):
    __tablename__ = "login_accounts"
    email = Column(String(254), primary_key=True)
    password_hash = Column(String, nullable=False)
    account_id = Column(Integer, ForeignKey("web_accounts.id"), unique=True)
    challenge = Column(String)
    issued = Column(Integer, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    digest = Column(String, primary_key=True)
    account_id = Column(Integer, ForeignKey("web_accounts.id"), nullable=False)
    expires = Column(BigInteger, nullable=False)


class Farmer(Base):
    __tablename__ = "farmers"

    user_id = Column(BigInteger, primary_key=True, index=True, autoincrement=False)
    name = Column(String, default="", nullable=False)
    city = Column(String, default="", nullable=False)
    location = Column(String, default="", nullable=False)
    crop = Column(String, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    history = relationship("History", back_populates="farmer", cascade="all, delete-orphan")

class FarmMemory(Base):
    __tablename__ = "farm_memory"
    user_id = Column(BigInteger, ForeignKey("farmers.user_id", ondelete="CASCADE"), primary_key=True)
    crop = Column(String, nullable=False)
    summary = Column(String(800), nullable=False)
    revision = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CropProfile(Base):
    __tablename__ = "crop_profiles"
    user_id = Column(BigInteger, ForeignKey("farmers.user_id", ondelete="CASCADE"), primary_key=True)
    state = Column(String(100), default="")
    stage = Column(String(40), default="")
    language = Column(String(60), default="")
    land_size = Column(String(60), default="")


class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("farmers.user_id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("Farmer", back_populates="history")
