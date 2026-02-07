#!/usr/bin/env python3
"""
VERIFICAÇÃO E SINCRONIZAÇÃO PÓS-IMPORTAÇÃO
==========================================

Este script verifica se os dados foram importados corretamente
e pode sincronizar automaticamente os campos calculados.

USO:
    python3 verificar_dados.py
"""

import psycopg2
import sys

# Configuração do banco
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def verificar_dados():
    """Verifica integridade dos dados após importação"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE DADOS PÓS-IMPORTAÇÃO")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("\n✅ Conectado ao banco Railway")
    except Exception as e:
        print(f"\n❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Estatísticas gerais
    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS GERAIS")
    print("=" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM series;")
    total_series = cursor.fetchone()[0]
    print(f"\n📚 Total de séries no banco: {total_series}")
    
    cursor.execute("SELECT COUNT(*) FROM issues;")
    total_issues = cursor.fetchone()[0]
    print(f"📖 Total de edições cadastradas: {total_issues}")
    
    # Verificar integridade: read_issues <= downloaded_issues <= total_issues
    print("\n" + "=" * 80)
    print("🔍 VERIFICANDO INTEGRIDADE DOS DADOS")
    print("=" * 80)
    
    cursor.execute("""
        SELECT id, title, read_issues, downloaded_issues, total_issues
        FROM series
        WHERE read_issues > downloaded_issues
           OR downloaded_issues > total_issues
    """)
    
    problemas = cursor.fetchall()
    
    if problemas:
        print(f"\n⚠️  Encontradas {len(problemas)} séries com dados inconsistentes:")
        for serie_id, title, read, downloaded, total in problemas:
            print(f"\n   ID {serie_id}: {title}")
            print(f"      Lendo: {read} | Baixado: {downloaded} | Total: {total}")
            if read > downloaded:
                print(f"      ⚠️  Lendo ({read}) > Baixado ({downloaded})")
            if downloaded > total:
                print(f"      ⚠️  Baixado ({downloaded}) > Total ({total})")
    else:
        print("\n✅ Todos os dados estão consistentes!")
    
    # Verificar séries sem edições cadastradas mas com read_issues > 0
    print("\n" + "=" * 80)
    print("🔍 VERIFICANDO SINCRONIZAÇÃO COM EDIÇÕES")
    print("=" * 80)
    
    cursor.execute("""
        SELECT s.id, s.title, s.read_issues, s.downloaded_issues,
               COUNT(i.id) as issues_count,
               COUNT(CASE WHEN i.is_read = true THEN 1 END) as read_count,
               COUNT(CASE WHEN i.is_downloaded = true THEN 1 END) as downloaded_count
        FROM series s
        LEFT JOIN issues i ON i.series_id = s.id
        GROUP BY s.id, s.title, s.read_issues, s.downloaded_issues
        HAVING (s.read_issues > 0 AND COUNT(i.id) = 0)
            OR (s.read_issues != COUNT(CASE WHEN i.is_read = true THEN 1 END))
            OR (s.downloaded_issues != COUNT(CASE WHEN i.is_downloaded = true THEN 1 END))
    """)
    
    dessinc = cursor.fetchall()
    
    if dessinc:
        print(f"\n⚠️  Encontradas {len(dessinc)} séries dessincronizadas:")
        print("\n   (Série tem valores em read_issues/downloaded_issues mas não tem edições cadastradas)")
        for serie_id, title, read_issues, downloaded_issues, issues_count, read_count, downloaded_count in dessinc[:10]:
            print(f"\n   ID {serie_id}: {title}")
            print(f"      Série: Lendo={read_issues}, Baixado={downloaded_issues}")
            print(f"      Edições: Total={issues_count}, Lidas={read_count}, Baixadas={downloaded_count}")
        
        if len(dessinc) > 10:
            print(f"\n   ... e mais {len(dessinc) - 10} séries")
    else:
        print("\n✅ Todas as séries estão sincronizadas com suas edições!")
    
    # Top 10 séries por número de edições
    print("\n" + "=" * 80)
    print("🏆 TOP 10 SÉRIES COM MAIS EDIÇÕES")
    print("=" * 80)
    
    cursor.execute("""
        SELECT title, total_issues, read_issues, downloaded_issues,
               CASE 
                   WHEN total_issues > 0 THEN ROUND((read_issues::numeric / total_issues * 100), 1)
                   ELSE 0
               END as progresso
        FROM series
        WHERE total_issues > 0
        ORDER BY total_issues DESC
        LIMIT 10
    """)
    
    top_series = cursor.fetchall()
    
    for idx, (title, total, read, downloaded, progresso) in enumerate(top_series, 1):
        print(f"\n{idx:2d}. {title}")
        print(f"    Total: {total} | Lendo: {read} | Baixado: {downloaded} | Progresso: {progresso}%")
    
    # Distribuição por tipo
    print("\n" + "=" * 80)
    print("📊 DISTRIBUIÇÃO POR TIPO")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            series_type,
            COUNT(*) as quantidade,
            ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM series) * 100, 1) as percentual
        FROM series
        GROUP BY series_type
        ORDER BY quantidade DESC
    """)
    
    tipos = cursor.fetchall()
    
    tipo_nomes = {
        'finalizada': 'Finalizada',
        'em_andamento': 'Em andamento',
        'lancamento': 'Lançamento',
        'edicao_especial': 'Edição Especial'
    }
    
    for tipo, qtd, pct in tipos:
        nome = tipo_nomes.get(tipo, tipo)
        barra = "█" * int(pct)
        print(f"\n{nome:20s}: {qtd:3d} ({pct:5.1f}%) {barra}")
    
    # Série concluídas vs não concluídas
    print("\n" + "=" * 80)
    print("📊 STATUS DE CONCLUSÃO")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            is_completed,
            COUNT(*) as quantidade
        FROM series
        GROUP BY is_completed
    """)
    
    for is_completed, qtd in cursor.fetchall():
        status = "✅ Finalizadas (não sairão mais edições)" if is_completed else "🔄 Não finalizadas (ainda podem ter novas edições)"
        print(f"\n{status}: {qtd}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ VERIFICAÇÃO CONCLUÍDA")
    print("=" * 80)
    
    if problemas or dessinc:
        print("\n⚠️  Foram encontrados problemas nos dados.")
        print("   Revise as mensagens acima e corrija se necessário.")
    else:
        print("\n✅ Todos os dados estão corretos e consistentes!")
    
    print("\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("=" * 80)

if __name__ == "__main__":
    try:
        verificar_dados()
    except KeyboardInterrupt:
        print("\n\n❌ Verificação cancelada")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
