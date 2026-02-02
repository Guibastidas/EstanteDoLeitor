"""
Script de importação de HQs do Excel para PostgreSQL/Railway
Adaptado para funcionar com SQLAlchemy e PostgreSQL
"""

import os
import sys
from datetime import datetime

print("=" * 70)
print("IMPORTAÇÃO DE HQS DO EXCEL PARA O RAILWAY")
print("=" * 70)

# Verificar DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("\n❌ DATABASE_URL não encontrada!")
    print("   Configure a variável de ambiente DATABASE_URL")
    sys.exit(1)

# Corrigir URL se necessário
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("\n[1/5] Verificando dependências...")

# Verificar imports
try:
    import pandas as pd
    print("✅ pandas importado")
except ImportError:
    print("❌ pandas não encontrado. Instale: pip install pandas openpyxl")
    sys.exit(1)

try:
    from sqlalchemy import create_engine, Column, Integer, String, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    print("✅ sqlalchemy importado")
except ImportError:
    print("❌ sqlalchemy não encontrado. Instale: pip install sqlalchemy")
    sys.exit(1)

try:
    import psycopg2
    print("✅ psycopg2 importado")
except ImportError:
    print("❌ psycopg2 não encontrado. Instale: pip install psycopg2-binary")
    sys.exit(1)

# Perguntar pelo arquivo Excel
print("\n[2/5] Procurando arquivo Excel...")
excel_file = input("Digite o caminho do arquivo Excel (ou Enter para 'Planilha_de_HQs.xlsx'): ").strip()
if not excel_file:
    excel_file = "Planilha_de_HQs.xlsx"

if not os.path.exists(excel_file):
    print(f"❌ Arquivo não encontrado: {excel_file}")
    print("\nArquivos disponíveis na pasta atual:")
    for f in os.listdir('.'):
        if f.endswith(('.xlsx', '.xls')):
            print(f"  - {f}")
    sys.exit(1)

print(f"✅ Arquivo encontrado: {excel_file}")

# Conectar ao banco
print("\n[3/5] Conectando ao PostgreSQL...")
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    # Definir modelo
    class ComicDB(Base):
        __tablename__ = "comics"
        
        id = Column(Integer, primary_key=True, index=True)
        title = Column(String(500), nullable=False)
        author = Column(String(200), nullable=True)
        publisher = Column(String(200), nullable=True)
        volume = Column(Integer, nullable=True)
        issue = Column(Integer, nullable=True)
        current_issue = Column(Integer, nullable=True, default=0)
        status = Column(String(50), nullable=False)
        cover_url = Column(Text, nullable=True)
        notes = Column(Text, nullable=True)
        date_added = Column(String(50), nullable=False)
        date_completed = Column(String(50), nullable=True)
    
    print("✅ Conectado ao PostgreSQL!")
    
    # CRIAR AS TABELAS ANTES DE USAR
    print("📋 Criando tabelas se não existirem...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas prontas!")
    
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    sys.exit(1)

# Verificar se já existem HQs
print("\n[4/5] Verificando banco de dados...")
db = SessionLocal()
count_existing = db.query(ComicDB).count()
print(f"📊 HQs no banco atualmente: {count_existing}")

if count_existing > 0:
    resposta = input("\n⚠️  Já existem HQs no banco. Deseja:\n  [1] Adicionar mais HQs (mantém as existentes)\n  [2] Limpar tudo e importar do zero\n  [3] Cancelar\nEscolha (1/2/3): ")
    
    if resposta == "2":
        print("\n🗑️  Removendo HQs existentes...")
        db.query(ComicDB).delete()
        db.commit()
        print("✅ Banco limpo!")
    elif resposta == "3":
        print("❌ Operação cancelada.")
        sys.exit(0)
    elif resposta != "1":
        print("❌ Opção inválida. Cancelando.")
        sys.exit(0)

# Ler planilha
print("\n[5/5] Lendo planilha Excel...")
try:
    df = pd.read_excel(excel_file)
    print(f"✅ {len(df)} linhas encontradas na planilha")
    
    # Mostrar colunas
    print(f"\nColunas encontradas: {list(df.columns)}")
    
except Exception as e:
    print(f"❌ Erro ao ler planilha: {e}")
    sys.exit(1)

# Função para determinar status
def determine_status(lendo, baixado):
    """Determina o status baseado no que está lendo vs baixado"""
    if lendo == 0:
        return 'para_ler'
    elif lendo >= baixado:
        return 'concluida'
    else:
        return 'lendo'

# Processar e importar
print("\n📚 Processando e importando HQs...")
print("-" * 70)

imported = 0
errors = 0
status_counts = {'para_ler': 0, 'lendo': 0, 'concluida': 0}

for idx, row in df.iterrows():
    try:
        # Ler dados da linha (adapte conforme suas colunas)
        nome = row.get('NOME', row.get('Nome', row.get('Título', row.get('Titulo', ''))))
        editora = row.get('EDITORA', row.get('Editora', None))
        
        # Ler números de edição
        lendo = int(row.get('Nº ISSUE LENDO', row.get('Lendo', row.get('Atual', 0))))
        baixado = int(row.get('Nº BAIXADO', row.get('Total', row.get('Baixado', lendo))))
        
        # Notas
        notas = row.get('NOTAS', row.get('Notas', row.get('Observações', None)))
        
        # Determinar status
        status = determine_status(lendo, baixado)
        status_counts[status] += 1
        
        # Criar registro
        date_added = datetime.now().isoformat()
        date_completed = datetime.now().isoformat() if status == 'concluida' else None
        
        comic = ComicDB(
            title=str(nome).strip(),
            publisher=str(editora).strip() if pd.notna(editora) and editora != '-' else None,
            issue=baixado,
            current_issue=lendo,
            status=status,
            notes=str(notas) if pd.notna(notas) else None,
            date_added=date_added,
            date_completed=date_completed
        )
        
        db.add(comic)
        imported += 1
        
        # Print progresso
        if imported % 10 == 0:
            print(f"  ✅ {imported} HQs importadas...")
        
    except Exception as e:
        errors += 1
        print(f"  ❌ Erro na linha {idx + 1}: {e}")

# Commit final
try:
    db.commit()
    print(f"\n✅ Commit realizado!")
except Exception as e:
    print(f"\n❌ Erro ao fazer commit: {e}")
    db.rollback()
    sys.exit(1)

db.close()

# Resumo final
print("\n" + "=" * 70)
print("🎉 IMPORTAÇÃO CONCLUÍDA!")
print("=" * 70)
print(f"\n📊 Resultado:")
print(f"   ✅ Importadas: {imported}")
print(f"   ❌ Erros: {errors}")
print(f"\n📚 Distribuição por status:")

status_names = {
    'para_ler': 'Para Ler',
    'lendo': 'Lendo',
    'concluida': 'Concluída'
}

for status, count in sorted(status_counts.items()):
    print(f"   {status_names[status]}: {count}")

# Verificar total final
db = SessionLocal()
total_final = db.query(ComicDB).count()
db.close()

print(f"\n🗄️  Total no banco agora: {total_final}")
print("\n🌐 Acesse seu app no Railway para ver as HQs!")
print("=" * 70)
