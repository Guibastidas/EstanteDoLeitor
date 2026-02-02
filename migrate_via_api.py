#!/usr/bin/env python3
"""
Script de Migração Simplificado: SQLite → PostgreSQL
Usa a API REST da aplicação para migrar dados
Não precisa de psycopg2!
"""

import sqlite3
import requests
import json
import os
from datetime import datetime


def connect_sqlite(db_path):
    """Conectar ao SQLite"""
    if not os.path.exists(db_path):
        print(f"❌ Arquivo {db_path} não encontrado!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar SQLite: {e}")
        return None


def get_api_url():
    """Pegar URL da API"""
    url = input("Cole a URL da sua aplicação no Railway (ex: https://seu-app.railway.app): ").strip()
    
    # Remover barra final se houver
    if url.endswith('/'):
        url = url[:-1]
    
    return url


def test_api_connection(api_url):
    """Testar se a API está acessível"""
    try:
        response = requests.get(f"{api_url}/stats", timeout=10)
        if response.status_code == 200:
            print("✅ API está acessível!")
            return True
        else:
            print(f"⚠️  API retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar à API: {e}")
        return False


def migrate_series(sqlite_conn, api_url):
    """Migrar séries via API"""
    print("\n📚 Migrando séries...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM series")
    series = cursor.fetchall()
    
    if not series:
        print("⚠️  Nenhuma série encontrada no SQLite")
        return 0
    
    success_count = 0
    error_count = 0
    
    for s in series:
        series_data = {
            "title": s['title'],
            "author": s['author'],
            "publisher": s['publisher'],
            "total_issues": s['total_issues'],
            "downloaded_issues": s['downloaded_issues'],
            "read_issues": s['read_issues'],
            "is_completed": bool(s['is_completed']),
            "series_type": s.get('series_type', 'em_andamento'),
            "cover_url": s['cover_url'],
            "notes": s['notes']
        }
        
        try:
            response = requests.post(
                f"{api_url}/series",
                json=series_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"  ✅ {s['title']}")
                success_count += 1
            else:
                print(f"  ❌ {s['title']} - Status {response.status_code}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ {s['title']} - Erro: {e}")
            error_count += 1
    
    print(f"\n📊 Resultado: {success_count} sucesso, {error_count} erros")
    return success_count


def get_series_mapping(api_url):
    """Obter mapeamento de séries antigas para novas (por título)"""
    try:
        response = requests.get(f"{api_url}/series", timeout=10)
        if response.status_code == 200:
            series_list = response.json()
            # Mapear por título
            return {s['title']: s['id'] for s in series_list}
        return {}
    except:
        return {}


def migrate_issues(sqlite_conn, api_url):
    """Migrar edições via API"""
    print("\n📖 Migrando edições...")
    
    # Primeiro, obter mapeamento de séries
    series_mapping = get_series_mapping(api_url)
    
    if not series_mapping:
        print("⚠️  Não foi possível obter lista de séries do PostgreSQL")
        return 0
    
    cursor = sqlite_conn.cursor()
    
    # Buscar edições com informações da série
    cursor.execute("""
        SELECT i.*, s.title as series_title
        FROM issues i
        JOIN series s ON i.series_id = s.id
    """)
    issues = cursor.fetchall()
    
    if not issues:
        print("⚠️  Nenhuma edição encontrada no SQLite")
        return 0
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for issue in issues:
        series_title = issue['series_title']
        
        # Encontrar ID da série no PostgreSQL
        if series_title not in series_mapping:
            print(f"  ⚠️  Série não encontrada: {series_title}")
            skipped_count += 1
            continue
        
        new_series_id = series_mapping[series_title]
        
        issue_data = {
            "issue_number": issue['issue_number'],
            "title": issue['title'],
            "is_read": bool(issue['is_read'])
        }
        
        try:
            response = requests.post(
                f"{api_url}/series/{new_series_id}/issues",
                json=issue_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"  ✅ {series_title} - Edição #{issue['issue_number']}")
                success_count += 1
            else:
                print(f"  ❌ {series_title} #{issue['issue_number']} - Status {response.status_code}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ {series_title} #{issue['issue_number']} - Erro: {e}")
            error_count += 1
    
    print(f"\n📊 Resultado: {success_count} sucesso, {error_count} erros, {skipped_count} puladas")
    return success_count


def main():
    print("=" * 70)
    print("🔄 MIGRAÇÃO SIMPLIFICADA: SQLite → PostgreSQL (via API)")
    print("=" * 70)
    print("\n⚠️  IMPORTANTE:")
    print("   - Este script usa a API REST da sua aplicação")
    print("   - A aplicação precisa estar RODANDO no Railway")
    print("   - Não precisa instalar psycopg2")
    print("=" * 70)
    
    # Caminho do SQLite
    sqlite_path = input("\nCaminho do arquivo SQLite (padrão: hq_manager.db): ").strip()
    if not sqlite_path:
        sqlite_path = "hq_manager.db"
    
    # Conectar SQLite
    print(f"\n📂 Conectando ao SQLite: {sqlite_path}")
    sqlite_conn = connect_sqlite(sqlite_path)
    if not sqlite_conn:
        return
    
    print("✅ SQLite conectado!")
    
    # Obter URL da API
    api_url = get_api_url()
    
    # Testar conexão com a API
    print(f"\n🌐 Testando conexão com: {api_url}")
    if not test_api_connection(api_url):
        print("\n❌ Não foi possível conectar à API")
        print("Verifique:")
        print("  1. A URL está correta?")
        print("  2. A aplicação está rodando no Railway?")
        print("  3. Você tem acesso à internet?")
        sqlite_conn.close()
        return
    
    # Confirmação
    print("\n⚠️  ATENÇÃO:")
    print("   - Novas séries serão criadas no PostgreSQL")
    print("   - Edições serão associadas às séries por nome")
    print("   - Séries duplicadas podem ser criadas se já existirem")
    
    confirm = input("\nDeseja continuar? (s/N): ").strip().lower()
    if confirm != 's':
        print("❌ Migração cancelada")
        sqlite_conn.close()
        return
    
    # Migrar dados
    series_count = migrate_series(sqlite_conn, api_url)
    
    if series_count > 0:
        input("\n⏸️  Pressione Enter para continuar com as edições...")
        issues_count = migrate_issues(sqlite_conn, api_url)
    else:
        issues_count = 0
    
    # Fechar conexão
    sqlite_conn.close()
    
    print("\n" + "=" * 70)
    print("✅ MIGRAÇÃO CONCLUÍDA!")
    print(f"   📚 Séries migradas: {series_count}")
    print(f"   📖 Edições migradas: {issues_count}")
    print("=" * 70)
    print("\n💡 Próximos passos:")
    print("   1. Acesse sua aplicação no Railway")
    print("   2. Verifique se as HQs aparecem")
    print("   3. Adicione URLs de capas às séries")
    print("   4. Faça backup do arquivo SQLite original")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migração cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
