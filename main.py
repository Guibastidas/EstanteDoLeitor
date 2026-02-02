from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

app = FastAPI(title="Estante do Leitor API", version="3.1")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== CONFIGURAÇÃO DO BANCO =====
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway/Produção - PostgreSQL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    print(f"✅ Usando PostgreSQL no Railway")
else:
    # Local - SQLite
    DATABASE_URL = "sqlite:///./hq_manager.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"✅ Usando SQLite local")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== MODELO DA TABELA COMICS =====
class Comic(Base):
    __tablename__ = "comics"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(200), nullable=True)
    publisher = Column(String(200), nullable=True)
    volume = Column(Integer, nullable=True)
    issue = Column(Integer, nullable=True)  # Total de edições baixadas
    current_issue = Column(Integer, nullable=True, default=0)  # Edições lidas
    status = Column(String(50), nullable=False)
    cover_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    date_added = Column(String(50), nullable=False)
    date_completed = Column(String(50), nullable=True)

# Criar tabelas
Base.metadata.create_all(bind=engine)
print("✅ Banco de dados inicializado!")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== MODELOS PYDANTIC =====
class ComicBase(BaseModel):
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[int] = None
    issue: Optional[int] = None
    current_issue: Optional[int] = 0
    status: str = 'para_ler'
    cover_url: Optional[str] = None
    notes: Optional[str] = None

class ComicCreate(ComicBase):
    pass

class ComicUpdate(ComicBase):
    title: Optional[str] = None
    status: Optional[str] = None

class ComicResponse(ComicBase):
    id: int
    date_added: str
    date_completed: Optional[str] = None
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total: int
    para_ler: int
    lendo: int
    concluidas: int

# ===== SERVIR ARQUIVOS ESTÁTICOS =====
@app.get("/styles.css")
async def serve_css():
    if os.path.exists("styles.css"):
        return FileResponse("styles.css", media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")

@app.get("/script.js")
async def serve_js():
    if os.path.exists("script.js"):
        return FileResponse("script.js", media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS not found")

@app.get("/script-extensions.js")
async def serve_extensions_js():
    if os.path.exists("script-extensions.js"):
        return FileResponse("script-extensions.js", media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Extensions JS not found")

# ===== ROTAS =====
@app.get("/")
async def root():
    """Rota raiz - serve o frontend"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "message": "Estante do Leitor API", 
        "version": "3.1",
        "status": "online",
        "database": "PostgreSQL (Railway)" if os.getenv("DATABASE_URL") else "SQLite (Local)"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check para o Railway - CORRIGIDO para SQLAlchemy 2.0"""
    try:
        # Usar select() corretamente no SQLAlchemy 2.0
        db.execute(select(Comic).limit(1))
        db_type = "PostgreSQL (Railway)" if os.getenv("DATABASE_URL") else "SQLite (Local)"
        return {
            "status": "healthy",
            "database": db_type,
            "connected": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Obter estatísticas gerais"""
    comics = db.query(Comic).all()
    
    total = len(comics)
    para_ler = sum(1 for c in comics if c.status == 'para_ler')
    lendo = sum(1 for c in comics if c.status == 'lendo')
    concluidas = sum(1 for c in comics if c.status == 'concluida')
    
    return {
        "total": total,
        "para_ler": para_ler,
        "lendo": lendo,
        "concluidas": concluidas
    }

@app.get("/series", response_model=List[ComicResponse])
async def get_series(search: Optional[str] = None, db: Session = Depends(get_db)):
    """Listar todas as HQs (compatibilidade com frontend)"""
    query = db.query(Comic)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Comic.title.ilike(search_filter)) |
            (Comic.author.ilike(search_filter)) |
            (Comic.publisher.ilike(search_filter))
        )
    
    comics = query.order_by(Comic.title).all()
    
    # Converter para formato esperado pelo frontend
    result = []
    for comic in comics:
        result.append({
            "id": comic.id,
            "title": comic.title,
            "author": comic.author,
            "publisher": comic.publisher,
            "total_issues": comic.issue or 0,
            "downloaded_issues": comic.issue or 0,
            "read_issues": comic.current_issue or 0,
            "cover_url": comic.cover_url,
            "notes": comic.notes,
            "date_added": comic.date_added,
            "date_updated": comic.date_completed,
            "is_completed": comic.status == 'concluida',
            "series_type": 'finalizada' if comic.status == 'concluida' else 'em_andamento',
            "status": comic.status
        })
    
    return result

@app.get("/series/{series_id}")
async def get_series_by_id(series_id: int, db: Session = Depends(get_db)):
    """Obter uma HQ específica"""
    comic = db.query(Comic).filter(Comic.id == series_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    
    return {
        "id": comic.id,
        "title": comic.title,
        "author": comic.author,
        "publisher": comic.publisher,
        "total_issues": comic.issue or 0,
        "downloaded_issues": comic.issue or 0,
        "read_issues": comic.current_issue or 0,
        "cover_url": comic.cover_url,
        "notes": comic.notes,
        "date_added": comic.date_added,
        "date_updated": comic.date_completed,
        "is_completed": comic.status == 'concluida',
        "series_type": 'finalizada' if comic.status == 'concluida' else 'em_andamento',
        "status": comic.status
    }

@app.post("/series", status_code=201)
async def create_series(data: dict, db: Session = Depends(get_db)):
    """Criar uma nova HQ"""
    # Verificar se já existe
    existing = db.query(Comic).filter(Comic.title == data['title']).first()
    if existing:
        raise HTTPException(status_code=400, detail="HQ já existe")
    
    # Determinar status
    read_issues = data.get('read_issues', 0)
    total_issues = data.get('total_issues', 0)
    
    if read_issues == 0:
        status = 'para_ler'
    elif read_issues >= total_issues and total_issues > 0:
        status = 'concluida'
    else:
        status = 'lendo'
    
    # Criar HQ
    comic = Comic(
        title=data['title'],
        author=data.get('author'),
        publisher=data.get('publisher'),
        issue=total_issues,
        current_issue=read_issues,
        status=status,
        cover_url=data.get('cover_url'),
        notes=data.get('notes'),
        date_added=datetime.now().isoformat(),
        date_completed=datetime.now().isoformat() if status == 'concluida' else None
    )
    
    db.add(comic)
    db.commit()
    db.refresh(comic)
    
    return {
        "id": comic.id,
        "title": comic.title,
        "author": comic.author,
        "publisher": comic.publisher,
        "total_issues": comic.issue or 0,
        "downloaded_issues": comic.issue or 0,
        "read_issues": comic.current_issue or 0,
        "cover_url": comic.cover_url,
        "notes": comic.notes,
        "date_added": comic.date_added,
        "date_updated": comic.date_completed,
        "is_completed": comic.status == 'concluida',
        "series_type": 'finalizada' if comic.status == 'concluida' else 'em_andamento',
        "status": comic.status
    }

@app.put("/series/{series_id}")
async def update_series(series_id: int, data: dict, db: Session = Depends(get_db)):
    """Atualizar uma HQ"""
    comic = db.query(Comic).filter(Comic.id == series_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    
    # Atualizar campos
    if 'title' in data:
        comic.title = data['title']
    if 'author' in data:
        comic.author = data['author']
    if 'publisher' in data:
        comic.publisher = data['publisher']
    if 'total_issues' in data:
        comic.issue = data['total_issues']
    if 'read_issues' in data:
        comic.current_issue = data['read_issues']
    if 'cover_url' in data:
        comic.cover_url = data['cover_url']
    if 'notes' in data:
        comic.notes = data['notes']
    
    # Atualizar status
    read_issues = data.get('read_issues', comic.current_issue or 0)
    total_issues = data.get('total_issues', comic.issue or 0)
    
    if read_issues == 0:
        comic.status = 'para_ler'
    elif read_issues >= total_issues and total_issues > 0:
        comic.status = 'concluida'
        comic.date_completed = datetime.now().isoformat()
    else:
        comic.status = 'lendo'
    
    db.commit()
    db.refresh(comic)
    
    return {
        "id": comic.id,
        "title": comic.title,
        "author": comic.author,
        "publisher": comic.publisher,
        "total_issues": comic.issue or 0,
        "downloaded_issues": comic.issue or 0,
        "read_issues": comic.current_issue or 0,
        "cover_url": comic.cover_url,
        "notes": comic.notes,
        "date_added": comic.date_added,
        "date_updated": comic.date_completed,
        "is_completed": comic.status == 'concluida',
        "series_type": 'finalizada' if comic.status == 'concluida' else 'em_andamento',
        "status": comic.status
    }

@app.delete("/series/{series_id}")
async def delete_series(series_id: int, db: Session = Depends(get_db)):
    """Deletar uma HQ"""
    comic = db.query(Comic).filter(Comic.id == series_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    
    db.delete(comic)
    db.commit()
    
    return {"message": "HQ deletada com sucesso"}

# Rotas de edições (simuladas para compatibilidade)
@app.get("/series/{series_id}/issues")
async def get_issues(series_id: int, db: Session = Depends(get_db)):
    """Listar edições (simulado)"""
    comic = db.query(Comic).filter(Comic.id == series_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    
    # Simular edições baseadas no total
    issues = []
    total = comic.issue or 0
    read = comic.current_issue or 0
    
    for i in range(1, total + 1):
        issues.append({
            "id": i,
            "series_id": series_id,
            "issue_number": i,
            "title": None,
            "is_read": i <= read,
            "is_downloaded": True,
            "date_added": comic.date_added,
            "date_read": comic.date_added if i <= read else None
        })
    
    return issues

@app.post("/series/{series_id}/issues", status_code=201)
async def create_issue(series_id: int, data: dict, db: Session = Depends(get_db)):
    """Adicionar edição (incrementa contador)"""
    comic = db.query(Comic).filter(Comic.id == series_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    
    # Incrementar total de edições
    comic.issue = (comic.issue or 0) + 1
    
    # Se marcado como lido, incrementar também current_issue
    if data.get('is_read', False):
        comic.current_issue = (comic.current_issue or 0) + 1
    
    # Atualizar status
    if comic.current_issue == 0:
        comic.status = 'para_ler'
    elif comic.current_issue >= comic.issue and comic.issue > 0:
        comic.status = 'concluida'
    else:
        comic.status = 'lendo'
    
    db.commit()
    db.refresh(comic)
    
    return {
        "id": comic.issue,
        "series_id": series_id,
        "issue_number": comic.issue,
        "title": None,
        "is_read": data.get('is_read', False),
        "is_downloaded": True,
        "date_added": datetime.now().isoformat(),
        "date_read": datetime.now().isoformat() if data.get('is_read') else None
    }

@app.put("/issues/{issue_id}")
async def update_issue(issue_id: int, data: dict):
    """Atualizar edição (não implementado - retorna sucesso)"""
    return {"message": "Edição atualizada (simulado)"}

@app.delete("/issues/{issue_id}")
async def delete_issue(issue_id: int):
    """Deletar edição (não implementado - retorna sucesso)"""
    return {"message": "Edição deletada (simulado)"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
