"""
Script de Migração: COMICS → SERIES
Converte dados da tabela 'comics' para o novo formato 'series' e 'issues'
"""

import os
import sys
from datetime import datetime

print("=" * 70)
print("MIGRAÇÃO: COMICS → SERIES")
print("=" * 70)

# Verificar DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("\n⚠️  DATABASE_URL não encontrada. Usando SQLite local...")
    DATABASE_URL = "sqlite:///./hq_manager.db"
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"\n✅ Conectando ao banco de dados...")

# Importar bibliotecas
try:
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey, inspect
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship
    print("✅ Bibliotecas importadas")
except ImportError as e:
    print(f"\n❌ Erro ao importar bibliotecas: {e}")
    print("   Instale: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# Criar engine
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base = declarative_base()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✅ Conectado ao banco!")
except Exception as e:
    print(f"\n❌ Erro ao conectar: {e}")
    sys.exit(1)

# Definir modelo ANTIGO (comics)
class ComicDB(Base):
    __tablename__ = "comics"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(200))
    publisher = Column(String(200))
    volume = Column(Integer)
    issue = Column(Integer, default=0)
    current_issue = Column(Integer, default=0)
    status = Column(String(50))
    cover_url = Column(Text)
    notes = Column(Text)
    date_added = Column(String(50))
    date_completed = Column(String(50))

# Definir modelo NOVO (series + issues)
class SeriesDB(Base):
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
    
    issues = relationship("IssueDB", back_populates="series", cascade="all, delete-orphan")


class IssueDB(Base):
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    issue_number = Column(Integer, nullable=False)
    title = Column(String(500))
    is_read = Column(Boolean, default=False)
    is_downloaded = Column(Boolean, default=True)
    date_added = Column(String(50), nullable=False)
    date_read = Column(String(50))
    
    series = relationship("SeriesDB", back_populates="issues")


# Verificar se tabela comics existe
print("\n📋 Verificando estrutura do banco...")
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

if "comics" not in existing_tables:
    print("\n⚠️  Tabela 'comics' não encontrada!")
    print("   Criando apenas as novas tabelas 'series' e 'issues'...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso!")
    print("\nVocê pode adicionar HQs manualmente pela interface.")
    sys.exit(0)

print("✅ Tabela 'comics' encontrada!")

# Verificar quantos registros existem
db = SessionLocal()
try:
    comics_count = db.query(ComicDB).count()
    print(f"📊 Total de HQs na tabela 'comics': {comics_count}")
    
    if comics_count == 0:
        print("\n⚠️  Nenhuma HQ encontrada para migrar.")
        print("   Criando novas tabelas vazias...")
        Base.metadata.create_all(bind=engine)
        print("✅ Pronto! Adicione HQs pela interface.")
        sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Erro ao verificar dados: {e}")
    db.close()
    sys.exit(1)

# Perguntar se quer migrar
print("\n" + "=" * 70)
print("OPÇÕES DE MIGRAÇÃO")
print("=" * 70)
print("\n[1] Migrar dados (cria tabelas 'series' e 'issues', mantém 'comics')")
print("[2] Migrar e limpar (remove tabela 'comics' após migração)")
print("[3] Apenas criar tabelas novas (não migra dados)")
print("[4] Cancelar")

choice = input("\nEscolha uma opção (1/2/3/4): ").strip()

if choice == "4":
    print("\n❌ Operação cancelada.")
    db.close()
    sys.exit(0)
elif choice == "3":
    print("\n📋 Criando apenas novas tabelas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas 'series' e 'issues' criadas!")
    db.close()
    sys.exit(0)
elif choice not in ["1", "2"]:
    print("\n❌ Opção inválida. Cancelando.")
    db.close()
    sys.exit(0)

# Criar novas tabelas
print("\n📋 Criando tabelas 'series' e 'issues'...")
Base.metadata.create_all(bind=engine)
print("✅ Tabelas criadas!")

# Verificar se já existem dados em 'series'
existing_series = db.query(SeriesDB).count()
if existing_series > 0:
    print(f"\n⚠️  Já existem {existing_series} séries na tabela 'series'!")
    overwrite = input("   Deseja adicionar mais ou limpar e migrar do zero? (adicionar/limpar): ").strip().lower()
    
    if overwrite == "limpar":
        print("\n🗑️  Limpando tabela 'series'...")
        db.query(SeriesDB).delete()
        db.commit()
        print("✅ Limpeza concluída!")

# Migrar dados
print("\n🔄 Iniciando migração de dados...")
print("-" * 70)

migrated = 0
errors = 0

comics = db.query(ComicDB).all()

for comic in comics:
    try:
        # Converter dados
        total_issues = comic.issue if comic.issue else 0
        read_issues = comic.current_issue if comic.current_issue else 0
        downloaded_issues = total_issues  # Assumir que todas as edições estão baixadas
        
        # Determinar se está completa
        is_completed = (read_issues >= total_issues) if total_issues > 0 else False
        
        # Data
        date_added = comic.date_added if comic.date_added else datetime.now().isoformat()
        
        # Criar série
        new_series = SeriesDB(
            title=comic.title,
            author=comic.author,
            publisher=comic.publisher,
            total_issues=total_issues,
            downloaded_issues=downloaded_issues,
            read_issues=read_issues,
            is_completed=is_completed,
            series_type='em_andamento',
            cover_url=comic.cover_url,
            notes=comic.notes,
            date_added=date_added,
            date_updated=comic.date_completed
        )
        
        db.add(new_series)
        db.flush()  # Para obter o ID
        
        # Criar edições (se houver)
        if total_issues > 0:
            for issue_num in range(1, total_issues + 1):
                issue = IssueDB(
                    series_id=new_series.id,
                    issue_number=issue_num,
                    title=f"Edição #{issue_num}",
                    is_read=(issue_num <= read_issues),
                    is_downloaded=True,
                    date_added=date_added,
                    date_read=date_added if issue_num <= read_issues else None
                )
                db.add(issue)
        
        migrated += 1
        
        if migrated % 10 == 0:
            print(f"  ✅ {migrated} HQs migradas...")
        
    except Exception as e:
        errors += 1
        print(f"  ❌ Erro ao migrar '{comic.title}': {e}")

# Commit
try:
    db.commit()
    print(f"\n✅ Migração concluída!")
except Exception as e:
    print(f"\n❌ Erro ao fazer commit: {e}")
    db.rollback()
    db.close()
    sys.exit(1)

# Verificar resultado
series_count = db.query(SeriesDB).count()
issues_count = db.query(IssueDB).count()

print("\n" + "=" * 70)
print("📊 RESULTADO DA MIGRAÇÃO")
print("=" * 70)
print(f"\n✅ Séries migradas: {migrated}")
print(f"❌ Erros: {errors}")
print(f"\n📚 Total de séries no banco: {series_count}")
print(f"📖 Total de edições no banco: {issues_count}")

# Opção 2: Limpar tabela comics
if choice == "2":
    print("\n" + "=" * 70)
    print("🗑️  LIMPEZA DA TABELA ANTIGA")
    print("=" * 70)
    
    confirm = input("\n⚠️  Confirma a exclusão da tabela 'comics'? (sim/não): ").strip().lower()
    
    if confirm == "sim":
        try:
            print("\n🗑️  Removendo tabela 'comics'...")
            ComicDB.__table__.drop(engine)
            print("✅ Tabela 'comics' removida com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao remover tabela: {e}")
    else:
        print("\n✅ Tabela 'comics' mantida (pode ser removida manualmente depois)")

db.close()

print("\n" + "=" * 70)
print("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 70)
print("\n🌐 Acesse seu app no Railway para ver as HQs migradas!")
print("\n📋 Próximos passos:")
print("   1. Teste a interface web")
print("   2. Verifique se todos os dados foram migrados corretamente")
print("   3. Se tudo estiver OK e escolheu opção 1, pode remover a tabela 'comics' manualmente")
print("\n" + "=" * 70)
