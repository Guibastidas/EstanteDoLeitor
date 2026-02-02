"""
Script de Migração: comics → series
Migra dados da tabela 'comics' para a nova tabela 'series' no PostgreSQL Railway
"""

import os
import sys
from datetime import datetime

print("=" * 70)
print("MIGRAÇÃO: TABELA COMICS → SERIES")
print("=" * 70)

# Verificar DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("\n❌ DATABASE_URL não encontrada!")
    print("   Configure a variável de ambiente DATABASE_URL do Railway")
    sys.exit(1)

# Corrigir URL se necessário
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"\n✅ DATABASE_URL configurada")

# Verificar dependências
print("\n[1/5] Verificando dependências...")
try:
    from sqlalchemy import create_engine, text, inspect
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

# Conectar ao banco
print("\n[2/5] Conectando ao PostgreSQL...")
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    conn = engine.connect()
    print("✅ Conectado ao PostgreSQL Railway")
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    sys.exit(1)

# Verificar se tabela comics existe
print("\n[3/5] Verificando tabelas...")
try:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    has_comics = 'comics' in tables
    has_series = 'series' in tables
    
    print(f"   Tabela 'comics': {'✅ existe' if has_comics else '❌ não existe'}")
    print(f"   Tabela 'series': {'✅ existe' if has_series else '❌ não existe'}")
    
    if not has_comics:
        print("\n❌ Tabela 'comics' não encontrada!")
        print("   Execute o main.py primeiro ou rode o import_excel_to_railway.py")
        sys.exit(1)
    
    # Contar registros em comics
    result = conn.execute(text("SELECT COUNT(*) FROM comics"))
    comics_count = result.scalar()
    print(f"\n📊 Registros na tabela comics: {comics_count}")
    
    if comics_count == 0:
        print("\n⚠️  Tabela comics está vazia! Nada para migrar.")
        sys.exit(0)
    
    # Se series não existe, criar
    if not has_series:
        print("\n📋 Criando tabela 'series'...")
        conn.execute(text("""
            CREATE TABLE series (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                author VARCHAR(200),
                publisher VARCHAR(200),
                total_issues INTEGER DEFAULT 0,
                downloaded_issues INTEGER DEFAULT 0,
                read_issues INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                series_type VARCHAR(50) DEFAULT 'em_andamento',
                cover_url TEXT,
                notes TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE issues (
                id SERIAL PRIMARY KEY,
                series_id INTEGER NOT NULL,
                issue_number INTEGER NOT NULL,
                title VARCHAR(500),
                is_read BOOLEAN DEFAULT FALSE,
                is_downloaded BOOLEAN DEFAULT FALSE,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_read TIMESTAMP
            )
        """))
        
        conn.commit()
        print("✅ Tabelas criadas!")
    
    # Verificar se já existem dados em series
    if has_series:
        result = conn.execute(text("SELECT COUNT(*) FROM series"))
        series_count = result.scalar()
        
        if series_count > 0:
            print(f"\n⚠️  Tabela 'series' já tem {series_count} registros!")
            resposta = input("\nDeseja:\n  [1] Adicionar mais (mantém existentes)\n  [2] Limpar tudo e migrar do zero\n  [3] Cancelar\nEscolha (1/2/3): ")
            
            if resposta == "2":
                print("\n🗑️  Removendo dados existentes...")
                conn.execute(text("DELETE FROM issues"))
                conn.execute(text("DELETE FROM series"))
                conn.commit()
                print("✅ Tabelas limpas!")
            elif resposta == "3":
                print("❌ Operação cancelada.")
                sys.exit(0)
            elif resposta != "1":
                print("❌ Opção inválida. Cancelando.")
                sys.exit(0)

except Exception as e:
    print(f"❌ Erro ao verificar tabelas: {e}")
    sys.exit(1)

# Ler dados da tabela comics
print("\n[4/5] Lendo dados da tabela comics...")
try:
    result = conn.execute(text("SELECT * FROM comics"))
    comics_list = result.fetchall()
    
    # Pegar nomes das colunas
    columns = result.keys()
    
    print(f"✅ {len(comics_list)} registros encontrados")
    print(f"   Colunas: {list(columns)}")
    
except Exception as e:
    print(f"❌ Erro ao ler dados: {e}")
    sys.exit(1)

# Migrar dados
print("\n[5/5] Migrando dados para 'series'...")
print("-" * 70)

migrated = 0
errors = 0

for row in comics_list:
    try:
        # Converter row em dict
        comic = dict(zip(columns, row))
        
        # Determinar series_type baseado em is_completed ou status
        series_type = 'em_andamento'
        
        # Alguns registros podem ter campo 'status'
        if 'status' in comic and comic['status']:
            status_val = str(comic['status']).lower()
            if 'conclu' in status_val or 'complet' in status_val:
                series_type = 'finalizada'
        
        # Converter is_completed (pode vir como 1/0 ou True/False)
        is_completed = False
        if 'is_completed' in comic and comic['is_completed']:
            is_completed = bool(comic['is_completed'])
            if is_completed:
                series_type = 'finalizada'
        
        # Preparar dados
        title = comic.get('title', 'Sem Título')
        author = comic.get('author')
        publisher = comic.get('publisher')
        
        # Campos de contagem
        total_issues = comic.get('issue', 0) or 0
        downloaded_issues = comic.get('issue', 0) or 0
        read_issues = comic.get('current_issue', 0) or 0
        
        cover_url = comic.get('cover_url')
        notes = comic.get('notes')
        
        # Datas
        date_added = comic.get('date_added', datetime.now().isoformat())
        date_updated = comic.get('date_completed') or datetime.now().isoformat()
        
        # Inserir na tabela series
        conn.execute(text("""
            INSERT INTO series 
            (title, author, publisher, total_issues, downloaded_issues, read_issues,
             is_completed, series_type, cover_url, notes, date_added, date_updated)
            VALUES 
            (:title, :author, :publisher, :total, :downloaded, :read,
             :completed, :type, :cover, :notes, :date_added, :date_updated)
        """), {
            'title': title,
            'author': author,
            'publisher': publisher,
            'total': total_issues,
            'downloaded': downloaded_issues,
            'read': read_issues,
            'completed': is_completed,
            'type': series_type,
            'cover': cover_url,
            'notes': notes,
            'date_added': date_added,
            'date_updated': date_updated
        })
        
        migrated += 1
        
        if migrated % 10 == 0:
            print(f"  ✅ {migrated} séries migradas...")
            
    except Exception as e:
        errors += 1
        title = comic.get('title', 'Desconhecido') if 'title' in comic else 'Desconhecido'
        print(f"  ❌ Erro na série '{title}': {e}")

# Commit final
try:
    conn.commit()
    print(f"\n✅ Commit realizado!")
except Exception as e:
    print(f"\n❌ Erro ao fazer commit: {e}")
    conn.rollback()
    sys.exit(1)

# Verificar total final
result = conn.execute(text("SELECT COUNT(*) FROM series"))
total_final = result.scalar()

conn.close()

# Resumo final
print("\n" + "=" * 70)
print("🎉 MIGRAÇÃO CONCLUÍDA!")
print("=" * 70)
print(f"\n📊 Resultado:")
print(f"   ✅ Migradas: {migrated}")
print(f"   ❌ Erros: {errors}")
print(f"\n🗄️  Total na tabela 'series' agora: {total_final}")
print("\n💡 Próximos passos:")
print("   1. Execute o main.py no Railway")
print("   2. Acesse seu app para ver as HQs")
print("   3. Opcional: delete a tabela 'comics' se quiser")
print("\n   Para deletar a tabela comics:")
print("   psql $DATABASE_URL -c 'DROP TABLE comics;'")
print("=" * 70)
