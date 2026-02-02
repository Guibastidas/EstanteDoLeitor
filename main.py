"""
HQ Manager - Backend FastAPI para PostgreSQL (Railway)
Sistema de gerenciamento de HQs com suporte a PostgreSQL
"""

import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==================== CONFIGURAÇÃO DO BANCO ====================

# Pegar DATABASE_URL do ambiente (Railway)
DATABASE_URL = os.getenv("DATABASE_URL")

# Se não tiver DATABASE_URL, usar SQLite local
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./hq_manager.db"
    print("⚠️  Usando SQLite local (desenvolvimento)")
else:
    # Corrigir URL do PostgreSQL se necessário
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"✅ Conectando ao PostgreSQL (Railway)")

# Criar engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # True para debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== MODELOS DO BANCO ====================

class SeriesDB(Base):
    """Modelo de Série no banco de dados"""
    __tablename__ = "series"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200))
    publisher = Column(String(200))
    total_issues = Column(Integer, default=0)
    downloaded_issues = Column(Integer, default=0)
    read_issues = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    series_type = Column(String(50), default='em_andamento')
    cover_url = Column(Text)
    notes = Column(Text)
    date_added = Column(DateTime, default=datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IssueDB(Base):
    """Modelo de Edição no banco de dados"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, nullable=False, index=True)
    issue_number = Column(Integer, nullable=False)
    title = Column(String(500))
    is_read = Column(Boolean, default=False)
    is_downloaded = Column(Boolean, default=False)
    date_added = Column(DateTime, default=datetime.utcnow)
    date_read = Column(DateTime)


# ==================== MODELOS PYDANTIC (API) ====================

class SeriesBase(BaseModel):
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    total_issues: int = 0
    downloaded_issues: int = 0
    read_issues: int = 0
    is_completed: bool = False
    series_type: str = 'em_andamento'
    cover_url: Optional[str] = None
    notes: Optional[str] = None


class SeriesCreate(SeriesBase):
    pass


class SeriesUpdate(SeriesBase):
    pass


class Series(SeriesBase):
    id: int
    status: str
    date_added: datetime
    date_updated: datetime
    
    class Config:
        from_attributes = True


class IssueBase(BaseModel):
    issue_number: int
    title: Optional[str] = None
    is_read: bool = False
    is_downloaded: bool = False


class IssueCreate(IssueBase):
    pass


class IssueUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_downloaded: Optional[bool] = None
    title: Optional[str] = None


class Issue(IssueBase):
    id: int
    series_id: int
    date_added: datetime
    date_read: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Stats(BaseModel):
    total: int
    para_ler: int
    lendo: int
    concluida: int


# ==================== LIFECYCLE ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar inicialização e finalização do app"""
    # Startup
    print("🚀 Iniciando HQ Manager...")
    print(f"📊 Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas!")
    
    yield
    
    # Shutdown
    print("👋 Encerrando HQ Manager...")


# ==================== APLICAÇÃO FASTAPI ====================

app = FastAPI(
    title="HQ Manager API",
    description="API para gerenciamento de HQs",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== FUNÇÕES AUXILIARES ====================

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def calculate_status(read_issues: int, total_issues: int) -> str:
    """Calcular status baseado no progresso de leitura"""
    if read_issues == 0:
        return "para_ler"
    elif read_issues >= total_issues and total_issues > 0:
        return "concluida"
    else:
        return "lendo"


def series_to_dict(series_db: SeriesDB) -> dict:
    """Converter SeriesDB para dict com status calculado"""
    status = calculate_status(series_db.read_issues, series_db.total_issues)
    
    return {
        "id": series_db.id,
        "title": series_db.title,
        "author": series_db.author,
        "publisher": series_db.publisher,
        "total_issues": series_db.total_issues,
        "downloaded_issues": series_db.downloaded_issues,
        "read_issues": series_db.read_issues,
        "is_completed": series_db.is_completed,
        "series_type": series_db.series_type,
        "cover_url": series_db.cover_url,
        "notes": series_db.notes,
        "status": status,
        "date_added": series_db.date_added.isoformat() if series_db.date_added else None,
        "date_updated": series_db.date_updated.isoformat() if series_db.date_updated else None
    }


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "HQ Manager API",
        "version": "2.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check para Railway"""
    return {"status": "healthy"}


# ==================== ENDPOINTS DE SÉRIES ====================

@app.get("/series")
async def list_series(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Listar todas as séries com filtros opcionais"""
    db = next(get_db())
    
    try:
        query = db.query(SeriesDB)
        
        # Filtro de busca
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (SeriesDB.title.ilike(search_pattern)) |
                (SeriesDB.author.ilike(search_pattern)) |
                (SeriesDB.publisher.ilike(search_pattern))
            )
        
        series_list = query.order_by(SeriesDB.title).all()
        
        # Converter para dict e calcular status
        result = []
        for series in series_list:
            series_dict = series_to_dict(series)
            
            # Filtro de status (após cálculo)
            if status and series_dict["status"] != status:
                continue
                
            result.append(series_dict)
        
        return result
        
    except Exception as e:
        print(f"Erro ao listar séries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/series/{series_id}")
async def get_series(series_id: int):
    """Obter uma série específica"""
    db = next(get_db())
    
    try:
        series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        
        if not series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        return series_to_dict(series)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao buscar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/series")
async def create_series(series: SeriesCreate):
    """Criar nova série"""
    db = next(get_db())
    
    try:
        # Criar série
        db_series = SeriesDB(
            title=series.title,
            author=series.author,
            publisher=series.publisher,
            total_issues=series.total_issues,
            downloaded_issues=series.downloaded_issues,
            read_issues=series.read_issues,
            is_completed=series.is_completed,
            series_type=series.series_type,
            cover_url=series.cover_url,
            notes=series.notes
        )
        
        db.add(db_series)
        db.commit()
        db.refresh(db_series)
        
        return series_to_dict(db_series)
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/series/{series_id}")
async def update_series(series_id: int, series: SeriesUpdate):
    """Atualizar série"""
    db = next(get_db())
    
    try:
        db_series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        
        if not db_series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        # Atualizar campos
        db_series.title = series.title
        db_series.author = series.author
        db_series.publisher = series.publisher
        db_series.total_issues = series.total_issues
        db_series.downloaded_issues = series.downloaded_issues
        db_series.read_issues = series.read_issues
        db_series.is_completed = series.is_completed
        db_series.series_type = series.series_type
        db_series.cover_url = series.cover_url
        db_series.notes = series.notes
        db_series.date_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(db_series)
        
        return series_to_dict(db_series)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/series/{series_id}")
async def delete_series(series_id: int):
    """Deletar série e suas edições"""
    db = next(get_db())
    
    try:
        db_series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        
        if not db_series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        # Deletar edições
        db.query(IssueDB).filter(IssueDB.series_id == series_id).delete()
        
        # Deletar série
        db.delete(db_series)
        db.commit()
        
        return {"message": "Série deletada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE EDIÇÕES ====================

@app.get("/series/{series_id}/issues")
async def list_issues(series_id: int):
    """Listar edições de uma série"""
    db = next(get_db())
    
    try:
        issues = db.query(IssueDB)\
            .filter(IssueDB.series_id == series_id)\
            .order_by(IssueDB.issue_number)\
            .all()
        
        return [
            {
                "id": issue.id,
                "series_id": issue.series_id,
                "issue_number": issue.issue_number,
                "title": issue.title,
                "is_read": issue.is_read,
                "is_downloaded": issue.is_downloaded,
                "date_added": issue.date_added.isoformat() if issue.date_added else None,
                "date_read": issue.date_read.isoformat() if issue.date_read else None
            }
            for issue in issues
        ]
        
    except Exception as e:
        print(f"Erro ao listar edições: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/series/{series_id}/issues")
async def create_issue(series_id: int, issue: IssueCreate):
    """Adicionar edição a uma série"""
    db = next(get_db())
    
    try:
        # Verificar se série existe
        series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        # Verificar se edição já existe
        existing = db.query(IssueDB)\
            .filter(IssueDB.series_id == series_id)\
            .filter(IssueDB.issue_number == issue.issue_number)\
            .first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Edição já existe")
        
        # Criar edição
        db_issue = IssueDB(
            series_id=series_id,
            issue_number=issue.issue_number,
            title=issue.title,
            is_read=issue.is_read,
            is_downloaded=issue.is_downloaded,
            date_read=datetime.utcnow() if issue.is_read else None
        )
        
        db.add(db_issue)
        
        # Atualizar contadores da série
        if issue.is_read:
            series.read_issues = max(series.read_issues, issue.issue_number)
        if issue.is_downloaded:
            series.downloaded_issues = max(series.downloaded_issues, issue.issue_number)
        
        series.date_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(db_issue)
        
        return {
            "id": db_issue.id,
            "series_id": db_issue.series_id,
            "issue_number": db_issue.issue_number,
            "title": db_issue.title,
            "is_read": db_issue.is_read,
            "is_downloaded": db_issue.is_downloaded,
            "date_added": db_issue.date_added.isoformat() if db_issue.date_added else None,
            "date_read": db_issue.date_read.isoformat() if db_issue.date_read else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar edição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/issues/{issue_id}")
async def update_issue(issue_id: int, issue_update: IssueUpdate):
    """Atualizar edição (marcar como lida, etc)"""
    db = next(get_db())
    
    try:
        db_issue = db.query(IssueDB).filter(IssueDB.id == issue_id).first()
        
        if not db_issue:
            raise HTTPException(status_code=404, detail="Edição não encontrada")
        
        # Atualizar campos
        if issue_update.is_read is not None:
            db_issue.is_read = issue_update.is_read
            db_issue.date_read = datetime.utcnow() if issue_update.is_read else None
        
        if issue_update.is_downloaded is not None:
            db_issue.is_downloaded = issue_update.is_downloaded
        
        if issue_update.title is not None:
            db_issue.title = issue_update.title
        
        # Atualizar contadores da série
        series = db.query(SeriesDB).filter(SeriesDB.id == db_issue.series_id).first()
        if series:
            # Recalcular read_issues
            read_count = db.query(func.count(IssueDB.id))\
                .filter(IssueDB.series_id == db_issue.series_id)\
                .filter(IssueDB.is_read == True)\
                .scalar()
            series.read_issues = read_count
            
            # Recalcular downloaded_issues
            downloaded_count = db.query(func.count(IssueDB.id))\
                .filter(IssueDB.series_id == db_issue.series_id)\
                .filter(IssueDB.is_downloaded == True)\
                .scalar()
            series.downloaded_issues = downloaded_count
            
            series.date_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(db_issue)
        
        return {
            "id": db_issue.id,
            "series_id": db_issue.series_id,
            "issue_number": db_issue.issue_number,
            "title": db_issue.title,
            "is_read": db_issue.is_read,
            "is_downloaded": db_issue.is_downloaded,
            "date_added": db_issue.date_added.isoformat() if db_issue.date_added else None,
            "date_read": db_issue.date_read.isoformat() if db_issue.date_read else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar edição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/issues/{issue_id}")
async def delete_issue(issue_id: int):
    """Deletar edição"""
    db = next(get_db())
    
    try:
        db_issue = db.query(IssueDB).filter(IssueDB.id == issue_id).first()
        
        if not db_issue:
            raise HTTPException(status_code=404, detail="Edição não encontrada")
        
        series_id = db_issue.series_id
        
        db.delete(db_issue)
        
        # Recalcular contadores da série
        series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        if series:
            read_count = db.query(func.count(IssueDB.id))\
                .filter(IssueDB.series_id == series_id)\
                .filter(IssueDB.is_read == True)\
                .scalar()
            series.read_issues = read_count
            
            downloaded_count = db.query(func.count(IssueDB.id))\
                .filter(IssueDB.series_id == series_id)\
                .filter(IssueDB.is_downloaded == True)\
                .scalar()
            series.downloaded_issues = downloaded_count
            
            series.date_updated = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Edição deletada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar edição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ESTATÍSTICAS ====================

@app.get("/stats")
async def get_stats():
    """Obter estatísticas gerais"""
    db = next(get_db())
    
    try:
        all_series = db.query(SeriesDB).all()
        
        stats = {
            "total": len(all_series),
            "para_ler": 0,
            "lendo": 0,
            "concluida": 0
        }
        
        for series in all_series:
            status = calculate_status(series.read_issues, series.total_issues)
            if status in stats:
                stats[status] += 1
        
        return stats
        
    except Exception as e:
        print(f"Erro ao calcular estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 70)
    print("HQ MANAGER API")
    print("=" * 70)
    print(f"🌐 Servidor rodando em: http://0.0.0.0:{port}")
    print(f"📚 Documentação: http://0.0.0.0:{port}/docs")
    print("=" * 70)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
