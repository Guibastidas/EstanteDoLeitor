"""
Configuração de Banco de Dados
Suporta tanto SQLite (local) quanto PostgreSQL (Railway)
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from typing import Generator

# Detectar ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway/Produção - PostgreSQL
    # Railway retorna postgres:// mas sqlalchemy precisa de postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
    print(f"✅ Usando PostgreSQL em produção")
else:
    # Local - SQLite
    DATABASE_URL = "sqlite:///./hq_manager.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"✅ Usando SQLite local")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos
class Series(Base):
    __tablename__ = "series"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, nullable=False, index=True)
    author = Column(String, nullable=True)
    publisher = Column(String, nullable=True, index=True)
    total_issues = Column(Integer, default=0)
    downloaded_issues = Column(Integer, default=0)
    read_issues = Column(Integer, default=0)
    cover_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    date_added = Column(String, nullable=False)
    date_updated = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    series_type = Column(String, default='em_andamento')
    
    # Relacionamento
    issues = relationship("Issue", back_populates="series", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    issue_number = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    is_downloaded = Column(Boolean, default=True)
    date_added = Column(String, nullable=False)
    date_read = Column(String, nullable=True)
    
    # Relacionamento
    series = relationship("Series", back_populates="issues")


def get_db() -> Generator:
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Criar todas as tabelas"""
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado!")
