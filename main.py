"""
HQ Manager - Backend FastAPI para PostgreSQL (Railway)
Sistema de gerenciamento de HQs usando tabela COMICS
"""

import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
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

class ComicDB(Base):
    """Modelo de HQ no banco de dados - TABELA COMICS"""
    __tablename__ = "comics"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200))
    publisher = Column(String(200))
    volume = Column(Integer)
    issue = Column(Integer, default=0)  # total_issues / downloaded_issues
    current_issue = Column(Integer, default=0)  # read_issues
    status = Column(String(50), nullable=False, default='para_ler')
    cover_url = Column(Text)
    notes = Column(Text)
    date_added = Column(String(50), nullable=False)
    date_completed = Column(String(50))


# CRIAR TABELAS AUTOMATICAMENTE SE NÃO EXISTIREM
print("🔍 Verificando se tabelas existem...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas com sucesso!")
except Exception as e:
    print(f"⚠️ Erro ao criar tabelas: {e}")
    print("   O sistema tentará funcionar mesmo assim...")


# ==================== MODELOS PYDANTIC (API) ====================

class ComicCreate(BaseModel):
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


class ComicUpdate(ComicCreate):
    pass


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
    description="API para gerenciamento de HQs - Tabela COMICS",
    version="2.1.0",
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

# Servir arquivos estáticos (CSS, JS, etc)
# Isso deve vir ANTES das rotas
import os
from pathlib import Path

# Verificar se os arquivos existem
current_dir = Path(__file__).parent
static_files = ["styles.css", "script.js", "script-extensions.js", "index.html"]

# Montar arquivos estáticos individualmente para garantir que funcionem
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


def comic_db_to_api(comic_db: ComicDB) -> dict:
    """Converter ComicDB para formato da API (compatível com frontend)"""
    # Usar issue como total_issues e current_issue como read_issues
    total_issues = comic_db.issue or 0
    read_issues = comic_db.current_issue or 0
    downloaded_issues = comic_db.issue or 0
    
    # Calcular status
    status = calculate_status(read_issues, total_issues)
    
    return {
        "id": comic_db.id,
        "title": comic_db.title,
        "author": comic_db.author,
        "publisher": comic_db.publisher,
        "total_issues": total_issues,
        "downloaded_issues": downloaded_issues,
        "read_issues": read_issues,
        "is_completed": status == "concluida",
        "series_type": "em_andamento",  # padrão
        "cover_url": comic_db.cover_url,
        "notes": comic_db.notes,
        "status": status,
        "date_added": comic_db.date_added,
        "date_updated": comic_db.date_completed
    }


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Servir página inicial"""
    return FileResponse("index.html")

@app.get("/api")
async def api_root():
    """Endpoint de informação da API"""
    return {
        "message": "HQ Manager API - Usando tabela COMICS",
        "version": "2.1.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check para Railway"""
    return {"status": "healthy"}


# ==================== ENDPOINTS DE SÉRIES (usando tabela comics) ====================

@app.get("/series")
async def list_series(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status")
):
    """Listar todas as HQs (series) com filtros opcionais"""
    db = next(get_db())
    
    try:
        query = db.query(ComicDB)
        
        # Filtro de busca
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ComicDB.title.ilike(search_pattern)) |
                (ComicDB.author.ilike(search_pattern)) |
                (ComicDB.publisher.ilike(search_pattern))
            )
        
        comics_list = query.order_by(ComicDB.title).all()
        
        # Converter para formato da API
        result = []
        for comic in comics_list:
            comic_dict = comic_db_to_api(comic)
            
            # Filtro de status (após cálculo)
            if status_filter and comic_dict["status"] != status_filter:
                continue
                
            result.append(comic_dict)
        
        return result
        
    except Exception as e:
        print(f"Erro ao listar séries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/series/{series_id}")
async def get_series(series_id: int):
    """Obter uma HQ específica"""
    db = next(get_db())
    
    try:
        comic = db.query(ComicDB).filter(ComicDB.id == series_id).first()
        
        if not comic:
            raise HTTPException(status_code=404, detail="HQ não encontrada")
        
        return comic_db_to_api(comic)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao buscar HQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/series")
async def create_series(series: ComicCreate):
    """Criar nova HQ"""
    db = next(get_db())
    
    try:
        # Calcular status
        status = calculate_status(series.read_issues, series.total_issues)
        
        # Criar comic
        db_comic = ComicDB(
            title=series.title,
            author=series.author,
            publisher=series.publisher,
            volume=None,
            issue=series.downloaded_issues,  # usar downloaded como issue
            current_issue=series.read_issues,
            status=status,
            cover_url=series.cover_url,
            notes=series.notes,
            date_added=datetime.now().isoformat(),
            date_completed=datetime.now().isoformat() if status == "concluida" else None
        )
        
        db.add(db_comic)
        db.commit()
        db.refresh(db_comic)
        
        return comic_db_to_api(db_comic)
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar HQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/series/{series_id}")
async def update_series(series_id: int, series: ComicUpdate):
    """Atualizar HQ"""
    db = next(get_db())
    
    try:
        db_comic = db.query(ComicDB).filter(ComicDB.id == series_id).first()
        
        if not db_comic:
            raise HTTPException(status_code=404, detail="HQ não encontrada")
        
        # Calcular status
        status = calculate_status(series.read_issues, series.total_issues)
        
        # Atualizar campos
        db_comic.title = series.title
        db_comic.author = series.author
        db_comic.publisher = series.publisher
        db_comic.issue = series.downloaded_issues
        db_comic.current_issue = series.read_issues
        db_comic.status = status
        db_comic.cover_url = series.cover_url
        db_comic.notes = series.notes
        db_comic.date_completed = datetime.now().isoformat() if status == "concluida" else None
        
        db.commit()
        db.refresh(db_comic)
        
        return comic_db_to_api(db_comic)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar HQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/series/{series_id}")
async def delete_series(series_id: int):
    """Deletar HQ"""
    db = next(get_db())
    
    try:
        db_comic = db.query(ComicDB).filter(ComicDB.id == series_id).first()
        
        if not db_comic:
            raise HTTPException(status_code=404, detail="HQ não encontrada")
        
        db.delete(db_comic)
        db.commit()
        
        return {"message": "HQ deletada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar HQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE EDIÇÕES (mock - não implementado) ====================

@app.get("/series/{series_id}/issues")
async def list_issues(series_id: int):
    """Listar edições de uma série (não implementado - retorna vazio)"""
    # A tabela comics não tem edições separadas
    return []


@app.post("/series/{series_id}/issues")
async def create_issue(series_id: int, issue: dict):
    """Adicionar edição (não implementado)"""
    raise HTTPException(
        status_code=501, 
        detail="Edições não suportadas com tabela comics. Use read_issues e downloaded_issues."
    )


@app.put("/issues/{issue_id}")
async def update_issue(issue_id: int, issue_update: dict):
    """Atualizar edição (não implementado)"""
    raise HTTPException(
        status_code=501, 
        detail="Edições não suportadas com tabela comics."
    )


@app.delete("/issues/{issue_id}")
async def delete_issue(issue_id: int):
    """Deletar edição (não implementado)"""
    raise HTTPException(
        status_code=501, 
        detail="Edições não suportadas com tabela comics."
    )


# ==================== ESTATÍSTICAS ====================

@app.get("/stats")
async def get_stats():
    """Obter estatísticas gerais"""
    db = next(get_db())
    
    try:
        all_comics = db.query(ComicDB).all()
        
        stats = {
            "total": len(all_comics),
            "para_ler": 0,
            "lendo": 0,
            "concluida": 0
        }
        
        for comic in all_comics:
            total_issues = comic.issue or 0
            read_issues = comic.current_issue or 0
            status = calculate_status(read_issues, total_issues)
            
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
    print("HQ MANAGER API - TABELA COMICS")
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
