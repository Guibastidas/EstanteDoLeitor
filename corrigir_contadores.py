#!/usr/bin/env python3
"""
CORREÇÃO: Recalcular contadores de edições
Recalcula read_issues e downloaded_issues baseado nas edições reais cadastradas
"""

import psycopg2
import sys

# Configuração do banco (Railway)
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def recalcular_contadores():
    print("=" * 70)
    print("🔧 CORREÇÃO: RECALCULAR CONTADORES DE EDIÇÕES")
    print("=" * 70)
    
    # Conectar ao PostgreSQL
    print("\n🔌 Conectando ao Railway...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Buscar todas as séries
    print("\n📚 Buscando séries...")
    cursor.execute("SELECT id, title, read_issues, downloaded_issues FROM series ORDER BY title;")
    series_list = cursor.fetchall()
    
    print(f"✅ {len(series_list)} séries encontradas")
    
    # Processar cada série
    print("\n🔄 Recalculando contadores...")
    print("-" * 70)
    
    corrigidas = 0
    sem_alteracao = 0
    
    for serie_id, titulo, read_atual, downloaded_atual in series_list:
        # Contar edições reais da série
        cursor.execute("""
            SELECT 
                COUNT(*) as total_downloaded,
                COUNT(CASE WHEN is_read = true THEN 1 END) as total_read
            FROM issues 
            WHERE series_id = %s
        """, (serie_id,))
        
        resultado = cursor.fetchone()
        downloaded_real = resultado[0] if resultado[0] else 0
        read_real = resultado[1] if resultado[1] else 0
        
        # Verificar se precisa atualizar
        if read_atual != read_real or downloaded_atual != downloaded_real:
            # Atualizar no banco
            cursor.execute("""
                UPDATE series 
                SET read_issues = %s, downloaded_issues = %s 
                WHERE id = %s
            """, (read_real, downloaded_real, serie_id))
            
            print(f"  ✏️ {titulo}")
            print(f"     Antes: Lendo={read_atual}, Baixadas={downloaded_atual}")
            print(f"     Depois: Lendo={read_real}, Baixadas={downloaded_real}")
            corrigidas += 1
        else:
            sem_alteracao += 1
    
    # Commit
    try:
        conn.commit()
        print(f"\n✅ Alterações salvas no banco!")
    except Exception as e:
        print(f"\n❌ Erro ao salvar: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ CORREÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   ✏️ Séries corrigidas: {corrigidas}")
    print(f"   ✅ Séries já corretas: {sem_alteracao}")
    print(f"   📚 Total de séries: {len(series_list)}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("\n💡 Os contadores agora refletem as edições realmente cadastradas!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        print("\n⚠️  Este script vai recalcular os contadores baseado nas edições cadastradas.")
        print("    Ele NÃO apaga edições, apenas corrige os números.\n")
        
        confirmacao = input("Deseja continuar? (s/n): ").strip().lower()
        
        if confirmacao in ['s', 'sim', 'y', 'yes']:
            recalcular_contadores()
        else:
            print("\n❌ Operação cancelada pelo usuário")
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
