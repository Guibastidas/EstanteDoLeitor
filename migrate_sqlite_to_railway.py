"""
Script de Migração: SQLite Local → PostgreSQL Railway (tabela comics)
Migra os dados do SQLite para a tabela 'comics' já existente no Railway
"""

import os
import sys
import sqlite3
from datetime import datetime

print("=" * 70)
print("MIGRAÇÃO: SQLite → PostgreSQL Railway (TABELA COMICS)")
print("=" * 70)

# Verificar DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("\n❌ DATABASE_URL não encontrada!")
    print("   Configure a variável de ambiente DATABASE_URL do Railway")
    print("\n   No Windows PowerShell:")
    print('   $env:DATABASE_URL="sua_url_aqui"')
    print("\n   No Windows CMD:")
    print('   set DATABASE_URL=sua_url_aqui')
    print("\n   No Linux/Mac:")
    print('   export DATABASE_URL="sua_url_aqui"')
    sys.exit(1)

# Corrigir URL se necessário
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"\n✅ DATABASE_URL configurada")

# Verificar dependências
print("\n[1/6] Verificando dependências...")
try:
    from sqlalchemy import create_engine, text
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

# Verificar arquivo SQLite local
print("\n[2/6] Verificando banco SQLite local...")
SQLITE_DB = "hq_manager.db"

if not os.path.exists(SQLITE_DB):
    print(f"❌ Banco SQLite não encontrado: {SQLITE_DB}")
    print("   Execute o sistema localmente primeiro para criar o banco")
    sys.exit(1)

print(f"✅ Banco SQLite encontrado: {SQLITE_DB}")

# Conectar aos bancos
print("\n[3/6] Conectando aos bancos de dados...")

# SQLite (origem)
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
print("✅ Conectado ao SQLite local")

# PostgreSQL (destino)
try:
    pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    pg_conn = pg_engine.connect()
    print("✅ Conectado ao PostgreSQL Railway")
except Exception as e:
    print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
    sys.exit(1)

# Verificar se tabela comics existe
print("\n[4/6] Verificando tabela 'comics' no Railway...")
try:
    result = pg_conn.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'comics'
    """))
    table_exists = result.scalar() > 0
    
    if not table_exists:
        print("⚠️  Tabela 'comics' não encontrada no Railway!")
        print("   Criando tabela 'comics'...")
        
        pg_conn.execute(text("""
            CREATE TABLE comics (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                author VARCHAR(200),
                publisher VARCHAR(200),
                volume INTEGER,
                issue INTEGER,
                current_issue INTEGER DEFAULT 0,
                status VARCHAR(50) NOT NULL,
                cover_url TEXT,
                notes TEXT,
                date_added VARCHAR(50) NOT NULL,
                date_completed VARCHAR(50)
            )
        """))
        pg_conn.commit()
        print("✅ Tabela 'comics' criada!")
    else:
        print("✅ Tabela 'comics' encontrada!")
        
        # Verificar quantos registros existem
        result = pg_conn.execute(text("SELECT COUNT(*) FROM comics"))
        count = result.scalar()
        print(f"📊 Registros existentes na tabela comics: {count}")
        
        if count > 0:
            resposta = input("\n⚠️  Já existem dados na tabela. Deseja:\n  [1] Adicionar mais (mantém existentes)\n  [2] Limpar tudo e importar do zero\n  [3] Cancelar\nEscolha (1/2/3): ")
            
            if resposta == "2":
                print("\n🗑️  Removendo dados existentes...")
                pg_conn.execute(text("DELETE FROM comics"))
                pg_conn.commit()
                print("✅ Tabela limpa!")
            elif resposta == "3":
                print("❌ Operação cancelada.")
                sys.exit(0)
            elif resposta != "1":
                print("❌ Opção inválida. Cancelando.")
                sys.exit(0)

except Exception as e:
    print(f"❌ Erro ao verificar tabela: {e}")
    sys.exit(1)

# Ler dados do SQLite
print("\n[5/6] Lendo dados do SQLite...")
cursor = sqlite_conn.cursor()

try:
    cursor.execute("SELECT * FROM series")
    series_list = cursor.fetchall()
    print(f"📚 Séries encontradas no SQLite: {len(series_list)}")
except Exception as e:
    print(f"❌ Erro ao ler dados do SQLite: {e}")
    sys.exit(1)

if len(series_list) == 0:
    print("\n⚠️  Não há dados para migrar!")
    sys.exit(0)

# Migrar dados
print("\n[6/6] Migrando dados...")
print("-" * 70)

migrated = 0
errors = 0

for row in series_list:
    try:
        # Determinar status baseado em read_issues e total_issues
        read_issues = row['read_issues'] or 0
        total_issues = row['total_issues'] or 0
        
        if read_issues == 0:
            status = 'para_ler'
        elif read_issues >= total_issues and total_issues > 0:
            status = 'concluida'
        else:
            status = 'lendo'
        
        # Inserir na tabela comics
        pg_conn.execute(text("""
            INSERT INTO comics 
            (title, author, publisher, issue, current_issue, status, 
             cover_url, notes, date_added, date_completed)
            VALUES 
            (:title, :author, :publisher, :issue, :current_issue, :status,
             :cover_url, :notes, :date_added, :date_completed)
        """), {
            'title': row['title'],
            'author': row['author'],
            'publisher': row['publisher'],
            'issue': row['downloaded_issues'] or 0,
            'current_issue': row['read_issues'] or 0,
            'status': status,
            'cover_url': row['cover_url'],
            'notes': row['notes'],
            'date_added': row['date_added'] or datetime.now().isoformat(),
            'date_completed': row['date_updated'] if status == 'concluida' else None
        })
        
        migrated += 1
        
        if migrated % 10 == 0:
            print(f"  ✅ {migrated} séries migradas...")
            
    except Exception as e:
        errors += 1
        print(f"  ❌ Erro na série '{row['title']}': {e}")

# Commit final
try:
    pg_conn.commit()
    print(f"\n✅ Commit realizado!")
except Exception as e:
    print(f"\n❌ Erro ao fazer commit: {e}")
    pg_conn.rollback()
    sys.exit(1)

# Fechar conexões
sqlite_conn.close()
pg_conn.close()

# Resumo final
print("\n" + "=" * 70)
print("🎉 MIGRAÇÃO CONCLUÍDA!")
print("=" * 70)
print(f"\n📊 Resultado:")
print(f"   ✅ Migradas: {migrated}")
print(f"   ❌ Erros: {errors}")

# Verificar total final
pg_conn = pg_engine.connect()
result = pg_conn.execute(text("SELECT COUNT(*) FROM comics"))
total_final = result.scalar()
pg_conn.close()

print(f"\n🗄️  Total no banco Railway agora: {total_final}")
print("\n🌐 Acesse seu app no Railway para ver as HQs!")
print("   URL: https://estantedoleitor.up.railway.app")
print("=" * 70)
