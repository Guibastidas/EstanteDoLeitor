"""
Script para criar a tabela COMICS no PostgreSQL do Railway
Execute este script UMA VEZ para criar a estrutura do banco
"""

import os
import sys

print("=" * 70)
print("CRIAÇÃO DA TABELA COMICS NO POSTGRESQL")
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

print(f"\n✅ DATABASE_URL encontrada")
print(f"   Conectando ao PostgreSQL...")

# Importar bibliotecas
try:
    from sqlalchemy import create_engine, Column, Integer, String, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    import psycopg2
except ImportError as e:
    print(f"\n❌ Erro ao importar bibliotecas: {e}")
    print("   Instale: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# Criar engine
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base = declarative_base()
    
    # Definir modelo da tabela COMICS
    class ComicDB(Base):
        __tablename__ = "comics"
        
        id = Column(Integer, primary_key=True, index=True)
        title = Column(String(500), nullable=False, index=True)
        author = Column(String(200))
        publisher = Column(String(200))
        volume = Column(Integer)
        issue = Column(Integer, default=0)
        current_issue = Column(Integer, default=0)
        status = Column(String(50), nullable=False, default='para_ler')
        cover_url = Column(Text)
        notes = Column(Text)
        date_added = Column(String(50), nullable=False)
        date_completed = Column(String(50))
    
    print("\n✅ Conectado ao PostgreSQL!")
    
    # Verificar se a tabela já existe
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "comics" in existing_tables:
        print("\n⚠️  A tabela 'comics' JÁ EXISTE no banco de dados!")
        print("   Deseja:")
        print("   [1] Manter a tabela existente (não fazer nada)")
        print("   [2] Recriar a tabela (APAGA TODOS OS DADOS!)")
        print("   [3] Cancelar")
        
        choice = input("\nEscolha (1/2/3): ").strip()
        
        if choice == "2":
            print("\n🗑️  Deletando tabela existente...")
            Base.metadata.drop_all(bind=engine)
            print("✅ Tabela deletada!")
            print("\n📋 Criando tabela novamente...")
            Base.metadata.create_all(bind=engine)
            print("✅ Tabela 'comics' criada com sucesso!")
        elif choice == "3":
            print("\n❌ Operação cancelada.")
            sys.exit(0)
        else:
            print("\n✅ Mantendo tabela existente.")
    else:
        print("\n📋 Criando tabela 'comics'...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabela 'comics' criada com sucesso!")
    
    # Verificar estrutura
    print("\n📊 Verificando estrutura da tabela...")
    columns = inspector.get_columns("comics")
    
    print("\nColunas da tabela 'comics':")
    for col in columns:
        col_type = str(col['type'])
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:20s} {col_type:20s} {nullable}")
    
    # Contar registros
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    count = db.query(ComicDB).count()
    db.close()
    
    print(f"\n📚 Total de registros na tabela: {count}")
    
    print("\n" + "=" * 70)
    print("✅ BANCO DE DADOS CONFIGURADO COM SUCESSO!")
    print("=" * 70)
    print("\n🎉 Agora você pode:")
    print("   1. Acessar a interface web em estantedoleitor.up.railway.app")
    print("   2. Adicionar HQs manualmente")
    print("   3. Importar de uma planilha Excel (use import_excel_to_railway.py)")
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\nDetalhes do erro:")
    import traceback
    traceback.print_exc()
    sys.exit(1)
