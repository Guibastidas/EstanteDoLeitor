from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3
import os

app = FastAPI(title="HQ Manager API")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "hq_manager.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabela de títulos (séries)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            author TEXT,
            publisher TEXT,
            total_issues INTEGER DEFAULT 0,
            downloaded_issues INTEGER DEFAULT 0,
            read_issues INTEGER DEFAULT 0,
            is_completed BOOLEAN DEFAULT 0,
            series_type TEXT DEFAULT 'em_andamento',
            cover_url TEXT,
            notes TEXT,
            date_added TEXT NOT NULL,
            date_updated TEXT
        )
    ''')
    
    # Adicionar coluna is_completed se não existir (para bancos antigos)
    try:
        cursor.execute("ALTER TABLE series ADD COLUMN is_completed BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    # Adicionar coluna series_type se não existir (para bancos antigos)
    try:
        cursor.execute("ALTER TABLE series ADD COLUMN series_type TEXT DEFAULT 'em_andamento'")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    # Tabela de edições
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            issue_number INTEGER NOT NULL,
            title TEXT,
            is_read BOOLEAN DEFAULT 0,
            is_downloaded BOOLEAN DEFAULT 1,
            date_added TEXT NOT NULL,
            date_read TEXT,
            FOREIGN KEY (series_id) REFERENCES series (id) ON DELETE CASCADE,
            UNIQUE(series_id, issue_number)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Modelos Pydantic
class IssueBase(BaseModel):
    issue_number: int
    title: Optional[str] = None
    is_read: bool = False
    is_downloaded: bool = True

class IssueCreate(IssueBase):
    pass

class Issue(IssueBase):
    id: int
    series_id: int
    date_added: str
    date_read: Optional[str] = None

class SeriesBase(BaseModel):
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    total_issues: int = 0
    downloaded_issues: int = 0
    read_issues: int = 0
    is_completed: bool = False
    series_type: str = "em_andamento"  # finalizada, em_andamento, lancamento, edicao_especial
    cover_url: Optional[str] = None
    notes: Optional[str] = None

class SeriesCreate(SeriesBase):
    pass

class SeriesUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    total_issues: Optional[int] = None
    downloaded_issues: Optional[int] = None
    read_issues: Optional[int] = None
    is_completed: Optional[bool] = None
    series_type: Optional[str] = None
    cover_url: Optional[str] = None
    notes: Optional[str] = None

class Series(SeriesBase):
    id: int
    date_added: str
    date_updated: Optional[str] = None
    status: str

# Funções auxiliares
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

def calculate_status(read_issues: int, total_issues: int) -> str:
    """Calcula o status baseado nas edições lidas"""
    if read_issues == 0:
        return "para_ler"
    elif read_issues >= total_issues:
        return "concluida"
    else:
        return "lendo"

# Rotas da API
@app.get("/")
def read_root():
    return {"message": "HQ Manager API is running"}

# SÉRIES
@app.get("/series", response_model=List[dict])
def get_series(search: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    if search:
        cursor.execute("""
            SELECT * FROM series 
            WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ?
            ORDER BY title
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM series ORDER BY title")
    
    series_list = cursor.fetchall()
    conn.close()
    
    # Adicionar status calculado
    for series in series_list:
        series['status'] = calculate_status(series['read_issues'], series['total_issues'])
    
    return series_list

@app.get("/series/{series_id}")
def get_series_by_id(series_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM series WHERE id = ?", (series_id,))
    series = cursor.fetchone()
    conn.close()
    
    if not series:
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    series['status'] = calculate_status(series['read_issues'], series['total_issues'])
    return series

@app.post("/series", response_model=dict)
def create_series(series: SeriesCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    date_added = datetime.now().isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO series (title, author, publisher, total_issues, downloaded_issues, 
                              read_issues, is_completed, series_type, cover_url, notes, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (series.title, series.author, series.publisher, series.total_issues,
              series.downloaded_issues, series.read_issues, series.is_completed,
              series.series_type, series.cover_url, series.notes, date_added))
        
        series_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Série com esse título já existe")
    
    conn.close()
    return get_series_by_id(series_id)

@app.put("/series/{series_id}")
def update_series(series_id: int, series: SeriesUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM series WHERE id = ?", (series_id,))
    existing = cursor.fetchone()
    
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    update_fields = []
    update_values = []
    
    if series.title is not None:
        update_fields.append("title = ?")
        update_values.append(series.title)
    if series.author is not None:
        update_fields.append("author = ?")
        update_values.append(series.author)
    if series.publisher is not None:
        update_fields.append("publisher = ?")
        update_values.append(series.publisher)
    if series.total_issues is not None:
        update_fields.append("total_issues = ?")
        update_values.append(series.total_issues)
    if series.downloaded_issues is not None:
        update_fields.append("downloaded_issues = ?")
        update_values.append(series.downloaded_issues)
    if series.read_issues is not None:
        update_fields.append("read_issues = ?")
        update_values.append(series.read_issues)
    if series.is_completed is not None:
        update_fields.append("is_completed = ?")
        update_values.append(series.is_completed)
    if series.series_type is not None:
        update_fields.append("series_type = ?")
        update_values.append(series.series_type)
    if series.cover_url is not None:
        update_fields.append("cover_url = ?")
        update_values.append(series.cover_url)
    if series.notes is not None:
        update_fields.append("notes = ?")
        update_values.append(series.notes)
    
    if update_fields:
        update_fields.append("date_updated = ?")
        update_values.append(datetime.now().isoformat())
        update_values.append(series_id)
        query = f"UPDATE series SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        conn.commit()
    
    conn.close()
    return get_series_by_id(series_id)

@app.delete("/series/{series_id}")
def delete_series(series_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM series WHERE id = ?", (series_id,))
    series = cursor.fetchone()
    
    if not series:
        conn.close()
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    cursor.execute("DELETE FROM series WHERE id = ?", (series_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Série deletada com sucesso"}

# EDIÇÕES
@app.get("/series/{series_id}/issues", response_model=List[Issue])
def get_issues(series_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se série existe
    cursor.execute("SELECT id FROM series WHERE id = ?", (series_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    cursor.execute("""
        SELECT * FROM issues 
        WHERE series_id = ? 
        ORDER BY issue_number
    """, (series_id,))
    
    issues = cursor.fetchall()
    conn.close()
    return issues

@app.post("/series/{series_id}/issues", response_model=Issue)
def create_issue(series_id: int, issue: IssueCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se série existe
    cursor.execute("SELECT id FROM series WHERE id = ?", (series_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Série não encontrada")
    
    date_added = datetime.now().isoformat()
    date_read = datetime.now().isoformat() if issue.is_read else None
    
    try:
        cursor.execute('''
            INSERT INTO issues (series_id, issue_number, title, is_read, is_downloaded, 
                              date_added, date_read)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (series_id, issue.issue_number, issue.title, issue.is_read, 
              issue.is_downloaded, date_added, date_read))
        
        issue_id = cursor.lastrowid
        
        # Atualizar contadores da série
        cursor.execute("""
            UPDATE series 
            SET downloaded_issues = (SELECT COUNT(*) FROM issues WHERE series_id = ? AND is_downloaded = 1),
                read_issues = (SELECT COUNT(*) FROM issues WHERE series_id = ? AND is_read = 1),
                date_updated = ?
            WHERE id = ?
        """, (series_id, series_id, datetime.now().isoformat(), series_id))
        
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Edição já existe para esta série")
    
    cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
    new_issue = cursor.fetchone()
    conn.close()
    return new_issue

@app.put("/issues/{issue_id}")
def update_issue(issue_id: int, is_read: bool):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT series_id FROM issues WHERE id = ?", (issue_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Edição não encontrada")
    
    series_id = result['series_id']
    date_read = datetime.now().isoformat() if is_read else None
    
    cursor.execute("""
        UPDATE issues 
        SET is_read = ?, date_read = ?
        WHERE id = ?
    """, (is_read, date_read, issue_id))
    
    # Atualizar contador de lidas na série
    cursor.execute("""
        UPDATE series 
        SET read_issues = (SELECT COUNT(*) FROM issues WHERE series_id = ? AND is_read = 1),
            date_updated = ?
        WHERE id = ?
    """, (series_id, datetime.now().isoformat(), series_id))
    
    conn.commit()
    conn.close()
    
    return {"message": "Edição atualizada com sucesso"}

@app.delete("/issues/{issue_id}")
def delete_issue(issue_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT series_id FROM issues WHERE id = ?", (issue_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Edição não encontrada")
    
    series_id = result['series_id']
    
    cursor.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    
    # Atualizar contadores
    cursor.execute("""
        UPDATE series 
        SET downloaded_issues = (SELECT COUNT(*) FROM issues WHERE series_id = ? AND is_downloaded = 1),
            read_issues = (SELECT COUNT(*) FROM issues WHERE series_id = ? AND is_read = 1),
            date_updated = ?
        WHERE id = ?
    """, (series_id, series_id, datetime.now().isoformat(), series_id))
    
    conn.commit()
    conn.close()
    
    return {"message": "Edição deletada com sucesso"}

# ESTATÍSTICAS
@app.get("/stats")
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM series")
    all_series = cursor.fetchall()
    
    total = len(all_series)
    para_ler = sum(1 for s in all_series if calculate_status(s['read_issues'], s['total_issues']) == 'para_ler')
    lendo = sum(1 for s in all_series if calculate_status(s['read_issues'], s['total_issues']) == 'lendo')
    concluidas = sum(1 for s in all_series if calculate_status(s['read_issues'], s['total_issues']) == 'concluida')
    
    total_issues = sum(s['total_issues'] for s in all_series)
    downloaded_issues = sum(s['downloaded_issues'] for s in all_series)
    read_issues = sum(s['read_issues'] for s in all_series)
    
    conn.close()
    
    return {
        "para_ler": para_ler,
        "lendo": lendo,
        "concluidas": concluidas,
        "total": total,
        "total_issues": total_issues,
        "downloaded_issues": downloaded_issues,
        "read_issues": read_issues
    }

# EXPORTAÇÃO
@app.post("/export-excel")
def export_to_excel():
    """Exporta dados para Excel"""
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    conn = get_db()
    
    # Ler dados das séries com TODOS os campos
    df = pd.read_sql_query("""
        SELECT 
            title as 'NOME',
            author as 'AUTOR',
            publisher as 'EDITORA',
            read_issues as 'Nº ISSUE LENDO',
            downloaded_issues as 'Nº BAIXADO',
            total_issues as 'TOTAL ISSUES',
            is_completed as 'FINALIZADA',
            CASE series_type
                WHEN 'finalizada' THEN 'Finalizada'
                WHEN 'em_andamento' THEN 'Em andamento'
                WHEN 'lancamento' THEN 'Lançamento'
                WHEN 'edicao_especial' THEN 'Edição Especial'
                ELSE 'Em andamento'
            END as 'TIPO',
            cover_url as 'CAPA',
            notes as 'NOTAS',
            date_added as 'DATA_ADICIONADA',
            date_updated as 'DATA_ATUALIZADA'
        FROM series
        ORDER BY title
    """, conn)
    
    conn.close()
    
    # Substituir None por string vazia
    df = df.fillna('')
    
    # Converter booleanos para texto legível
    df['FINALIZADA'] = df['FINALIZADA'].apply(lambda x: 'Sim' if x == 1 or x == True else 'Não' if x == 0 or x == False else '')
    
    # Criar arquivo Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='HQs')
        
        # Ajustar largura das colunas
        worksheet = writer.sheets['HQs']
        col_widths = {
            'NOME': 40,
            'AUTOR': 30,
            'EDITORA': 25,
            'Nº ISSUE LENDO': 15,
            'Nº BAIXADO': 15,
            'TOTAL ISSUES': 15,
            'FINALIZADA': 12,
            'TIPO': 18,
            'CAPA': 60,
            'NOTAS': 40,
            'DATA_ADICIONADA': 20,
            'DATA_ATUALIZADA': 20
        }
        
        for idx, col in enumerate(df.columns):
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            width = col_widths.get(col, 15)
            worksheet.column_dimensions[col_letter].width = width
    
    output.seek(0)
    
    filename = f"Planilha_de_HQs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
