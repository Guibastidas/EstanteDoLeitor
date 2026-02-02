from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, case
import os

# Importar configuração do banco
from database import get_db, init_db, Series as DBSeries, Issue as DBIssue

app = FastAPI(title="Estante do Leitor API", version="2.1")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar banco de dados
init_db()

# Servir arquivos estáticos
if os.path.exists("index.html"):
    app.mount("/static", StaticFiles(directory="."), name="static")

# Modelos Pydantic
class IssueBase(BaseModel):
    issue_number: int
    title: Optional[str] = None
    is_read: bool = False
    is_downloaded: bool = True

class IssueCreate(IssueBase):
    pass

class IssueUpdate(BaseModel):
    is_read: Optional[bool] = None
    title: Optional[str] = None

class IssueResponse(IssueBase):
    id: int
    series_id: int
    date_added: str
    date_read: Optional[str] = None
    
    class Config:
        from_attributes = True

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
    title: Optional[str] = None

class SeriesResponse(SeriesBase):
    id: int
    date_added: str
    date_updated: Optional[str] = None
    status: str = 'para_ler'
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total: int
    para_ler: int
    lendo: int
    concluidas: int

# Funções auxiliares
def calculate_status(series: DBSeries) -> str:
    """Calcula o status da série"""
    if series.read_issues == 0:
        return 'para_ler'
    elif series.read_issues >= series.total_issues and series.total_issues > 0:
        return 'concluida'
    else:
        return 'lendo'

def series_to_response(series: DBSeries) -> dict:
    """Converte Series do banco para resposta"""
    return {
        **{k: v for k, v in series.__dict__.items() if not k.startswith('_')},
        "status": calculate_status(series)
    }

# Rotas
@app.get("/")
async def root():
    """Rota raiz - redireciona para o frontend"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "message": "Estante do Leitor API", 
        "version": "2.1",
        "status": "online",
        "database": "PostgreSQL" if os.getenv("DATABASE_URL") else "SQLite"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check para o Railway"""
    try:
        # Testar conexão com banco
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Obter estatísticas gerais"""
    series_list = db.query(DBSeries).all()
    
    total = len(series_list)
    para_ler = sum(1 for s in series_list if s.read_issues == 0)
    concluidas = sum(1 for s in series_list if s.read_issues >= s.total_issues and s.total_issues > 0)
    lendo = total - para_ler - concluidas
    
    return {
        "total": total,
        "para_ler": para_ler,
        "lendo": lendo,
        "concluidas": concluidas
    }

@app.get("/series", response_model=List[SeriesResponse])
async def get_series(search: Optional[str] = None, db: Session = Depends(get_db)):
    """Listar todas as séries com busca opcional"""
    query = db.query(DBSeries)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (DBSeries.title.ilike(search_filter)) |
            (DBSeries.author.ilike(search_filter)) |
            (DBSeries.publisher.ilike(search_filter))
        )
    
    series_list = query.order_by(DBSeries.title).all()
    return [series_to_response(s) for s in series_list]

@app.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series_by_id(series_id: int, db: Session = Depends(get_db)):
    """Obter uma série específica"""
    series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    return series_to_response(series)

@app.post("/series", response_model=SeriesResponse, status_code=201)
async def create_series(series: SeriesCreate, db: Session = Depends(get_db)):
    """Criar uma nova série"""
    # Verificar se já existe
    existing = db.query(DBSeries).filter(DBSeries.title == series.title).first()
    if existing:
        raise HTTPException(status_code=400, detail="Série já existe")
    
    # Criar série
    db_series = DBSeries(
        **series.dict(),
        date_added=datetime.now().isoformat()
    )
    
    db.add(db_series)
    db.commit()
    db.refresh(db_series)
    
    # Criar issues se downloaded_issues > 0
    if series.downloaded_issues > 0:
        date_now = datetime.now().isoformat()
        for issue_num in range(1, series.downloaded_issues + 1):
            is_read = issue_num <= series.read_issues
            db_issue = DBIssue(
                series_id=db_series.id,
                issue_number=issue_num,
                is_read=is_read,
                is_downloaded=True,
                date_added=date_now,
                date_read=date_now if is_read else None
            )
            db.add(db_issue)
        db.commit()
    
    return series_to_response(db_series)

@app.put("/series/{series_id}", response_model=SeriesResponse)
async def update_series(series_id: int, series_update: SeriesUpdate, db: Session = Depends(get_db)):
    """Atualizar uma série"""
    db_series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if not db_series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    # Atualizar campos
    update_data = series_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_series, key, value)
    
    db_series.date_updated = datetime.now().isoformat()
    
    db.commit()
    db.refresh(db_series)
    
    return series_to_response(db_series)

@app.delete("/series/{series_id}")
async def delete_series(series_id: int, db: Session = Depends(get_db)):
    """Deletar uma série"""
    db_series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if not db_series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    db.delete(db_series)
    db.commit()
    
    return {"message": "Série deletada com sucesso"}

# Rotas de Issues (Edições)
@app.get("/series/{series_id}/issues", response_model=List[IssueResponse])
async def get_issues(series_id: int, db: Session = Depends(get_db)):
    """Listar todas as edições de uma série"""
    # Verificar se série existe
    series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    issues = db.query(DBIssue).filter(
        DBIssue.series_id == series_id
    ).order_by(DBIssue.issue_number).all()
    
    return issues

@app.post("/series/{series_id}/issues", response_model=IssueResponse, status_code=201)
async def create_issue(series_id: int, issue: IssueCreate, db: Session = Depends(get_db)):
    """Adicionar uma nova edição"""
    # Verificar se série existe
    series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    # Verificar se edição já existe
    existing = db.query(DBIssue).filter(
        DBIssue.series_id == series_id,
        DBIssue.issue_number == issue.issue_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Edição já existe")
    
    # Criar edição
    db_issue = DBIssue(
        series_id=series_id,
        **issue.dict(),
        date_added=datetime.now().isoformat(),
        date_read=datetime.now().isoformat() if issue.is_read else None
    )
    
    db.add(db_issue)
    
    # Atualizar contadores da série
    series.downloaded_issues = db.query(func.count(DBIssue.id)).filter(
        DBIssue.series_id == series_id
    ).scalar()
    
    series.read_issues = db.query(func.count(DBIssue.id)).filter(
        DBIssue.series_id == series_id,
        DBIssue.is_read == True
    ).scalar()
    
    series.date_updated = datetime.now().isoformat()
    
    db.commit()
    db.refresh(db_issue)
    
    return db_issue

@app.put("/issues/{issue_id}", response_model=IssueResponse)
async def update_issue(issue_id: int, issue_update: IssueUpdate, db: Session = Depends(get_db)):
    """Atualizar uma edição (marcar como lida/não lida)"""
    db_issue = db.query(DBIssue).filter(DBIssue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Edição não encontrada")
    
    # Atualizar campos
    update_data = issue_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_issue, key, value)
    
    # Atualizar date_read
    if 'is_read' in update_data:
        db_issue.date_read = datetime.now().isoformat() if update_data['is_read'] else None
    
    # Atualizar contador da série
    series = db.query(DBSeries).filter(DBSeries.id == db_issue.series_id).first()
    if series:
        series.read_issues = db.query(func.count(DBIssue.id)).filter(
            DBIssue.series_id == db_issue.series_id,
            DBIssue.is_read == True
        ).scalar()
        series.date_updated = datetime.now().isoformat()
    
    db.commit()
    db.refresh(db_issue)
    
    return db_issue

@app.delete("/issues/{issue_id}")
async def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    """Deletar uma edição"""
    db_issue = db.query(DBIssue).filter(DBIssue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Edição não encontrada")
    
    series_id = db_issue.series_id
    
    db.delete(db_issue)
    
    # Atualizar contadores da série
    series = db.query(DBSeries).filter(DBSeries.id == series_id).first()
    if series:
        series.downloaded_issues = db.query(func.count(DBIssue.id)).filter(
            DBIssue.series_id == series_id
        ).scalar()
        
        series.read_issues = db.query(func.count(DBIssue.id)).filter(
            DBIssue.series_id == series_id,
            DBIssue.is_read == True
        ).scalar()
        
        series.date_updated = datetime.now().isoformat()
    
    db.commit()
    
    return {"message": "Edição deletada com sucesso"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
