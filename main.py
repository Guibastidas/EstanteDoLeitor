"""
HQ Manager - Backend FastAPI com PostgreSQL
Sistema de gerenciamento de HQs com tabelas SERIES e ISSUES
"""

import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# ==================== CONFIGURAÇÃO DO BANCO ====================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./hq_manager.db"
    print("⚠️  Usando SQLite local (desenvolvimento)")
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"✅ Conectando ao PostgreSQL (Railway)")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== MODELOS DO BANCO ====================

class SeriesDB(Base):
    """Modelo de Série de HQ no banco de dados"""
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
    date_added = Column(String(50), nullable=False)
    date_updated = Column(String(50))
    
    # Relacionamento
    issues = relationship("IssueDB", back_populates="series", cascade="all, delete-orphan")


class IssueDB(Base):
    """Modelo de Edição de HQ no banco de dados"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    issue_number = Column(Integer, nullable=False)
    title = Column(String(500))
    is_read = Column(Boolean, default=False)
    is_downloaded = Column(Boolean, default=True)
    date_added = Column(String(50), nullable=False)
    date_read = Column(String(50))
    
    # Relacionamento
    series = relationship("SeriesDB", back_populates="issues")


# CRIAR TABELAS AUTOMATICAMENTE
print("📝 Verificando se tabelas existem...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas com sucesso!")
except Exception as e:
    print(f"⚠️ Erro ao criar tabelas: {e}")

# ==================== MODELOS PYDANTIC (API) ====================

class SeriesCreate(BaseModel):
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


class SeriesUpdate(SeriesCreate):
    pass


class SeriesResponse(BaseModel):
    id: int
    title: str
    author: Optional[str]
    publisher: Optional[str]
    total_issues: int
    downloaded_issues: int
    read_issues: int
    is_completed: bool
    series_type: str
    cover_url: Optional[str]
    notes: Optional[str]
    status: str
    date_added: str
    date_updated: Optional[str]
    
    class Config:
        from_attributes = True


class IssueCreate(BaseModel):
    issue_number: int
    title: Optional[str] = None
    is_read: bool = False


class IssueUpdate(BaseModel):
    is_read: bool


class IssueResponse(BaseModel):
    id: int
    series_id: int
    issue_number: int
    title: Optional[str]
    is_read: bool
    is_downloaded: bool
    date_added: str
    date_read: Optional[str]
    
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
    print("🚀 Iniciando HQ Manager...")
    Base.metadata.create_all(bind=engine)
    print("✅ Banco pronto!")
    yield
    print("👋 Encerrando HQ Manager...")


# ==================== APLICAÇÃO FASTAPI ====================

app = FastAPI(
    title="HQ Manager API",
    description="API para gerenciamento de HQs",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DEPENDENCY ====================

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== FUNÇÕES AUXILIARES ====================

def calculate_status(read_issues: int, total_issues: int) -> str:
    """Calcular status baseado no progresso"""
    if read_issues == 0:
        return "para_ler"
    elif read_issues >= total_issues and total_issues > 0:
        return "concluida"
    else:
        return "lendo"


def series_to_response(series: SeriesDB) -> dict:
    """Converter SeriesDB para resposta da API"""
    status = calculate_status(series.read_issues, series.total_issues)
    
    return {
        "id": series.id,
        "title": series.title,
        "author": series.author,
        "publisher": series.publisher,
        "total_issues": series.total_issues,
        "downloaded_issues": series.downloaded_issues,
        "read_issues": series.read_issues,
        "is_completed": series.is_completed,
        "series_type": series.series_type,
        "cover_url": series.cover_url,
        "notes": series.notes,
        "status": status,
        "date_added": series.date_added,
        "date_updated": series.date_updated
    }


# ==================== SERVIR ARQUIVOS ESTÁTICOS ====================

@app.get("/styles.css")
async def get_styles():
    """Servir arquivo CSS"""
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="text/css")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CSS not found")


@app.get("/script.js")
async def get_script():
    """Servir arquivo JavaScript principal"""
    try:
        with open("script.js", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JS not found")


@app.get("/script-extensions.js")
async def get_script_extensions():
    """Servir arquivo JavaScript de extensões"""
    try:
        with open("script-extensions.js", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JS extensions not found")


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Servir página inicial"""
    return FileResponse("index.html")


@app.get("/api")
async def api_root():
    """Endpoint de informação da API"""
    return {
        "message": "HQ Manager API",
        "version": "3.0.0",
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
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Listar todas as séries com filtros opcionais"""
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
        
        # Converter para resposta
        result = []
        for series in series_list:
            series_dict = series_to_response(series)
            
            # Filtro de status (após cálculo)
            if status and series_dict["status"] != status:
                continue
                
            result.append(series_dict)
        
        return result
        
    except Exception as e:
        print(f"Erro ao listar séries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/series/{series_id}")
async def get_series(series_id: int, db: Session = Depends(get_db)):
    """Obter uma série específica"""
    try:
        series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        
        if not series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        return series_to_response(series)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao buscar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/series")
async def create_series(series: SeriesCreate, db: Session = Depends(get_db)):
    """Criar nova série"""
    try:
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
            notes=series.notes,
            date_added=datetime.now().isoformat(),
            date_updated=datetime.now().isoformat()
        )
        
        db.add(db_series)
        db.commit()
        db.refresh(db_series)
        
        return series_to_response(db_series)
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/series/{series_id}")
async def update_series(series_id: int, series: SeriesUpdate, db: Session = Depends(get_db)):
    """Atualizar série"""
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
        db_series.date_updated = datetime.now().isoformat()
        
        db.commit()
        db.refresh(db_series)
        
        return series_to_response(db_series)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar série: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/series/{series_id}")
async def delete_series(series_id: int, db: Session = Depends(get_db)):
    """Deletar série"""
    try:
        db_series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        
        if not db_series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
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
async def list_issues(series_id: int, db: Session = Depends(get_db)):
    """Listar edições de uma série"""
    try:
        issues = db.query(IssueDB).filter(IssueDB.series_id == series_id).order_by(IssueDB.issue_number).all()
        
        return [
            {
                "id": issue.id,
                "series_id": issue.series_id,
                "issue_number": issue.issue_number,
                "title": issue.title,
                "is_read": issue.is_read,
                "is_downloaded": issue.is_downloaded,
                "date_added": issue.date_added,
                "date_read": issue.date_read
            }
            for issue in issues
        ]
        
    except Exception as e:
        print(f"Erro ao listar edições: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/series/{series_id}/issues")
async def create_issue(series_id: int, issue: IssueCreate, db: Session = Depends(get_db)):
    """Adicionar edição a uma série"""
    try:
        # Verificar se série existe
        series = db.query(SeriesDB).filter(SeriesDB.id == series_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Série não encontrada")
        
        # Criar edição
        db_issue = IssueDB(
            series_id=series_id,
            issue_number=issue.issue_number,
            title=issue.title,
            is_read=issue.is_read,
            is_downloaded=True,
            date_added=datetime.now().isoformat(),
            date_read=datetime.now().isoformat() if issue.is_read else None
        )
        
        db.add(db_issue)
        
        # Atualizar contadores da série
        series.downloaded_issues += 1
        if issue.is_read:
            series.read_issues += 1
        
        db.commit()
        db.refresh(db_issue)
        
        return {
            "id": db_issue.id,
            "series_id": db_issue.series_id,
            "issue_number": db_issue.issue_number,
            "title": db_issue.title,
            "is_read": db_issue.is_read,
            "is_downloaded": db_issue.is_downloaded,
            "date_added": db_issue.date_added,
            "date_read": db_issue.date_read
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar edição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/issues/{issue_id}")
async def update_issue(issue_id: int, issue_update: IssueUpdate, db: Session = Depends(get_db)):
    """Atualizar edição (marcar como lida/não lida)"""
    try:
        db_issue = db.query(IssueDB).filter(IssueDB.id == issue_id).first()
        
        if not db_issue:
            raise HTTPException(status_code=404, detail="Edição não encontrada")
        
        # Atualizar status de leitura
        was_read = db_issue.is_read
        db_issue.is_read = issue_update.is_read
        
        if issue_update.is_read and not was_read:
            db_issue.date_read = datetime.now().isoformat()
            # Incrementar contador da série
            series = db.query(SeriesDB).filter(SeriesDB.id == db_issue.series_id).first()
            if series:
                series.read_issues += 1
        elif not issue_update.is_read and was_read:
            db_issue.date_read = None
            # Decrementar contador da série
            series = db.query(SeriesDB).filter(SeriesDB.id == db_issue.series_id).first()
            if series:
                series.read_issues = max(0, series.read_issues - 1)
        
        db.commit()
        db.refresh(db_issue)
        
        return {
            "id": db_issue.id,
            "series_id": db_issue.series_id,
            "issue_number": db_issue.issue_number,
            "title": db_issue.title,
            "is_read": db_issue.is_read,
            "is_downloaded": db_issue.is_downloaded,
            "date_added": db_issue.date_added,
            "date_read": db_issue.date_read
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar edição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/issues/{issue_id}")
async def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    """Deletar edição"""
    try:
        db_issue = db.query(IssueDB).filter(IssueDB.id == issue_id).first()
        
        if not db_issue:
            raise HTTPException(status_code=404, detail="Edição não encontrada")
        
        # Atualizar contadores da série
        series = db.query(SeriesDB).filter(SeriesDB.id == db_issue.series_id).first()
        if series:
            series.downloaded_issues = max(0, series.downloaded_issues - 1)
            if db_issue.is_read:
                series.read_issues = max(0, series.read_issues - 1)
        
        db.delete(db_issue)
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
async def get_stats(db: Session = Depends(get_db)):
    """Obter estatísticas gerais"""
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
    print(f"🌐 Servidor: http://0.0.0.0:{port}")
    print(f"📚 Docs: http://0.0.0.0:{port}/docs")
    print("=" * 70)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
