"""
Script de Sincronização - SQLite Local → PostgreSQL Railway
Migra todos os dados do banco local para o PostgreSQL na nuvem
"""

import os
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ========================================
# CONFIGURAÇÃO - COLE A URL DO RAILWAY AQUI
# ========================================

# Copie a "Connection URL" da segunda imagem e cole aqui:
RAILWAY_DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

# ⚠️ IMPORTANTE: Substitua a URL acima pela sua URL completa do Railway!
# Você encontra ela em: PostgreSQL > Connect > Public Network > Connection URL

# ========================================
# NÃO PRECISA ALTERAR DAQUI PARA BAIXO
# ========================================

# Banco local
LOCAL_DB = "hq_manager.db"

def verificar_configuracao():
    """Verificar se a URL foi configurada"""
    if "********" in RAILWAY_DATABASE_URL:
        print("\n" + "=" * 70)
        print("❌ ERRO: Você precisa configurar a URL do PostgreSQL!")
        print("=" * 70)
        print("\n📋 PASSOS:")
        print("1. No Railway, clique no serviço PostgreSQL")
        print("2. Vá em 'Connect'")
        print("3. Clique na aba 'Public Network'")
        print("4. Copie a 'Connection URL' completa")
        print("5. Cole no topo deste arquivo na variável RAILWAY_DATABASE_URL")
        print("\nExemplo:")
        print('RAILWAY_DATABASE_URL = "postgresql://postgres:senha@host:15604/railway"')
        print("\n" + "=" * 70)
        return False
    return True

def testar_conexoes():
    """Testar conexões com ambos os bancos"""
    print("\n🔍 Testando conexões...")
    
    # Testar SQLite local
    if not os.path.exists(LOCAL_DB):
        print(f"❌ Banco local não encontrado: {LOCAL_DB}")
        return False
    print(f"✅ Banco local encontrado: {LOCAL_DB}")
    
    # Testar PostgreSQL Railway
    try:
        engine = create_engine(RAILWAY_DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅ Conexão com Railway estabelecida!")
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar no Railway: {e}")
        print("\n💡 Dicas:")
        print("   - Verifique se a URL está correta")
        print("   - Verifique se o PostgreSQL está rodando no Railway")
        print("   - Tente usar a aba 'Public Network' para obter a URL")
        return False

def criar_tabelas_railway(engine):
    """Criar tabelas no PostgreSQL se não existirem"""
    print("\n🔧 Criando tabelas no PostgreSQL...")
    
    with engine.connect() as conn:
        # Criar tabela series
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS series (
                id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL UNIQUE,
                author VARCHAR,
                publisher VARCHAR,
                total_issues INTEGER DEFAULT 0,
                downloaded_issues INTEGER DEFAULT 0,
                read_issues INTEGER DEFAULT 0,
                cover_url TEXT,
                notes TEXT,
                date_added VARCHAR NOT NULL,
                date_updated VARCHAR,
                is_completed BOOLEAN DEFAULT false,
                series_type VARCHAR DEFAULT 'em_andamento'
            )
        """))
        
        # Criar tabela issues
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS issues (
                id SERIAL PRIMARY KEY,
                series_id INTEGER NOT NULL,
                issue_number INTEGER NOT NULL,
                title VARCHAR,
                is_read BOOLEAN DEFAULT false,
                is_downloaded BOOLEAN DEFAULT true,
                date_added VARCHAR NOT NULL,
                date_read VARCHAR,
                CONSTRAINT fk_series
                    FOREIGN KEY(series_id) 
                    REFERENCES series(id)
                    ON DELETE CASCADE,
                CONSTRAINT unique_series_issue 
                    UNIQUE(series_id, issue_number)
            )
        """))
        
        # Criar índices
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_series_title ON series(title)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_series_publisher ON series(publisher)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_issues_series_id ON issues(series_id)"))
        
        conn.commit()
    
    print("✅ Tabelas criadas com sucesso!")

def sincronizar_dados():
    """Sincronizar dados do SQLite para PostgreSQL"""
    
    print("\n" + "=" * 70)
    print("🚀 INICIANDO SINCRONIZAÇÃO")
    print("=" * 70)
    
    # Verificar configuração
    if not verificar_configuracao():
        return
    
    # Testar conexões
    if not testar_conexoes():
        return
    
    # Conectar aos bancos
    local_conn = sqlite3.connect(LOCAL_DB)
    local_conn.row_factory = sqlite3.Row
    local_cursor = local_conn.cursor()
    
    railway_engine = create_engine(RAILWAY_DATABASE_URL)
    
    # Criar tabelas
    criar_tabelas_railway(railway_engine)
    
    # Contar dados locais
    local_cursor.execute("SELECT COUNT(*) FROM series")
    total_series = local_cursor.fetchone()[0]
    
    local_cursor.execute("SELECT COUNT(*) FROM issues")
    total_issues = local_cursor.fetchone()[0]
    
    print(f"\n📊 Dados no banco local:")
    print(f"   Séries: {total_series}")
    print(f"   Edições: {total_issues}")
    
    if total_series == 0:
        print("\n⚠️ Nenhuma série encontrada no banco local!")
        print("💡 Execute primeiro: python importar_planilha.py")
        return
    
    # Confirmar
    print(f"\n⚠️ ATENÇÃO: Você está prestes a sincronizar {total_series} séries e {total_issues} edições")
    print("   do banco LOCAL para o PostgreSQL no RAILWAY")
    confirmar = input("\n❓ Deseja continuar? (s/n): ").strip().lower()
    
    if confirmar != 's':
        print("❌ Sincronização cancelada")
        return
    
    print("\n⏳ Sincronizando dados...")
    
    series_importadas = 0
    series_atualizadas = 0
    issues_importadas = 0
    erros = []
    
    with railway_engine.connect() as railway_conn:
        # Mapear IDs antigos para novos
        id_map = {}
        
        # Sincronizar séries
        local_cursor.execute("SELECT * FROM series ORDER BY id")
        series_list = local_cursor.fetchall()
        
        for serie in series_list:
            try:
                # Verificar se já existe
                result = railway_conn.execute(
                    text("SELECT id FROM series WHERE title = :title"),
                    {"title": serie['title']}
                ).fetchone()
                
                if result:
                    # Atualizar
                    series_id = result[0]
                    
                    # Converter booleanos do SQLite (0/1) para PostgreSQL (True/False)
                    is_completed_bool = bool(serie['is_completed']) if serie['is_completed'] is not None else False
                    
                    railway_conn.execute(text("""
                        UPDATE series 
                        SET author = :author,
                            publisher = :publisher,
                            total_issues = :total_issues,
                            downloaded_issues = :downloaded_issues,
                            read_issues = :read_issues,
                            cover_url = :cover_url,
                            notes = :notes,
                            is_completed = :is_completed,
                            series_type = :series_type,
                            date_updated = :date_updated
                        WHERE id = :id
                    """), {
                        'author': serie['author'],
                        'publisher': serie['publisher'],
                        'total_issues': serie['total_issues'],
                        'downloaded_issues': serie['downloaded_issues'],
                        'read_issues': serie['read_issues'],
                        'cover_url': serie['cover_url'],
                        'notes': serie['notes'],
                        'is_completed': is_completed_bool,
                        'series_type': serie['series_type'],
                        'date_updated': datetime.now().isoformat(),
                        'id': series_id
                    })
                    series_atualizadas += 1
                    print(f"  ↻ {serie['title']} - ATUALIZADA")
                else:
                    # Inserir nova
                    # Converter booleanos do SQLite (0/1) para PostgreSQL (True/False)
                    is_completed_bool = bool(serie['is_completed']) if serie['is_completed'] is not None else False
                    
                    result = railway_conn.execute(text("""
                        INSERT INTO series 
                        (title, author, publisher, total_issues, downloaded_issues, read_issues,
                         cover_url, notes, is_completed, series_type, date_added)
                        VALUES 
                        (:title, :author, :publisher, :total_issues, :downloaded_issues, :read_issues,
                         :cover_url, :notes, :is_completed, :series_type, :date_added)
                        RETURNING id
                    """), {
                        'title': serie['title'],
                        'author': serie['author'],
                        'publisher': serie['publisher'],
                        'total_issues': serie['total_issues'],
                        'downloaded_issues': serie['downloaded_issues'],
                        'read_issues': serie['read_issues'],
                        'cover_url': serie['cover_url'],
                        'notes': serie['notes'],
                        'is_completed': is_completed_bool,
                        'series_type': serie['series_type'],
                        'date_added': serie['date_added']
                    })
                    series_id = result.fetchone()[0]
                    series_importadas += 1
                    print(f"  ✓ {serie['title']} - NOVA")
                
                # Mapear ID antigo para novo
                id_map[serie['id']] = series_id
                
            except Exception as e:
                erros.append(f"Série '{serie['title']}': {str(e)}")
                print(f"  ✗ ERRO em {serie['title']}: {e}")
                railway_conn.rollback()  # Importante: fazer rollback para não travar transação
                continue
        
        railway_conn.commit()
        
        # Sincronizar edições
        print(f"\n📖 Sincronizando edições...")
        local_cursor.execute("SELECT * FROM issues ORDER BY series_id, issue_number")
        issues_list = local_cursor.fetchall()
        
        for issue in issues_list:
            try:
                # Pegar novo ID da série
                new_series_id = id_map.get(issue['series_id'])
                if not new_series_id:
                    continue
                
                # Verificar se já existe
                result = railway_conn.execute(text("""
                    SELECT id FROM issues 
                    WHERE series_id = :series_id AND issue_number = :issue_number
                """), {
                    'series_id': new_series_id,
                    'issue_number': issue['issue_number']
                }).fetchone()
                
                if not result:
                    # Inserir edição
                    # Converter booleanos do SQLite (0/1) para PostgreSQL (True/False)
                    is_read_bool = bool(issue['is_read']) if issue['is_read'] is not None else False
                    is_downloaded_bool = bool(issue['is_downloaded']) if issue['is_downloaded'] is not None else True
                    
                    railway_conn.execute(text("""
                        INSERT INTO issues
                        (series_id, issue_number, title, is_read, is_downloaded, date_added, date_read)
                        VALUES
                        (:series_id, :issue_number, :title, :is_read, :is_downloaded, :date_added, :date_read)
                    """), {
                        'series_id': new_series_id,
                        'issue_number': issue['issue_number'],
                        'title': issue['title'],
                        'is_read': is_read_bool,
                        'is_downloaded': is_downloaded_bool,
                        'date_added': issue['date_added'],
                        'date_read': issue['date_read']
                    })
                    issues_importadas += 1
                
            except Exception as e:
                erros.append(f"Edição {issue['issue_number']}: {str(e)}")
        
        railway_conn.commit()
    
    local_conn.close()
    
    # Resumo final
    print("\n" + "=" * 70)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Estatísticas:")
    print(f"   ✨ Séries novas: {series_importadas}")
    print(f"   ↻ Séries atualizadas: {series_atualizadas}")
    print(f"   📖 Edições sincronizadas: {issues_importadas}")
    
    if erros:
        print(f"\n⚠️ Erros encontrados: {len(erros)}")
        for erro in erros[:5]:
            print(f"   • {erro}")
        if len(erros) > 5:
            print(f"   ... e mais {len(erros) - 5} erros")
    
    print(f"\n🎉 Seus dados agora estão no Railway!")
    print(f"   Acesse: https://seu-app.up.railway.app")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        sincronizar_dados()
    except KeyboardInterrupt:
        print("\n\n❌ Sincronização cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
