#!/usr/bin/env python3
"""
SINCRONIZAÇÃO: Atualizar campo "Lendo" baseado nos dados da tabela SERIES
Este script pega o valor de read_issues da tabela series e marca as edições
correspondentes na tabela issues como lidas (is_read = TRUE)
"""

import psycopg2
import sys

# Configuração do banco (Railway)
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def sincronizar_campo_lendo():
    print("=" * 70)
    print("🔄 SINCRONIZAÇÃO: CAMPO 'LENDO' - SERIES → ISSUES")
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
    
    # Buscar todas as séries que têm read_issues > 0
    print("\n📚 Buscando séries com edições lidas...")
    cursor.execute("""
        SELECT id, title, read_issues, total_issues 
        FROM series 
        WHERE read_issues > 0
        ORDER BY title;
    """)
    series_list = cursor.fetchall()
    
    print(f"✅ {len(series_list)} séries encontradas com edições lidas")
    
    if len(series_list) == 0:
        print("\n💡 Nenhuma série tem o campo read_issues preenchido.")
        print("   Verifique se você importou os dados da planilha corretamente.")
        cursor.close()
        conn.close()
        return
    
    # Processar cada série
    print("\n🔄 Sincronizando edições...")
    print("-" * 70)
    
    total_atualizadas = 0
    total_criadas = 0
    series_processadas = 0
    
    for serie_id, titulo, read_issues, total_issues in series_list:
        print(f"\n📖 {titulo}")
        print(f"   Deveria ter {read_issues} edições lidas")
        
        # Verificar quantas edições existem para esta série
        cursor.execute("""
            SELECT COUNT(*) 
            FROM issues 
            WHERE series_id = %s
        """, (serie_id,))
        total_cadastradas = cursor.fetchone()[0]
        
        print(f"   Edições cadastradas: {total_cadastradas}")
        
        # Se não tem nenhuma edição cadastrada, precisamos criar
        if total_cadastradas == 0:
            print(f"   ⚠️  Nenhuma edição cadastrada!")
            print(f"   Criando {read_issues} edições e marcando como lidas...")
            
            for numero in range(1, read_issues + 1):
                try:
                    cursor.execute("""
                        INSERT INTO issues (series_id, issue_number, is_read, is_downloaded, date_added)
                        VALUES (%s, %s, TRUE, TRUE, NOW())
                    """, (serie_id, numero))
                    total_criadas += 1
                except Exception as e:
                    print(f"      ❌ Erro ao criar edição #{numero}: {e}")
            
            print(f"   ✅ {read_issues} edições criadas e marcadas como lidas")
        
        else:
            # Se já tem edições cadastradas, atualizar as primeiras N como lidas
            print(f"   Marcando as primeiras {read_issues} edições como lidas...")
            
            # Buscar os IDs das edições existentes (ordenadas por número)
            cursor.execute("""
                SELECT id, issue_number, is_read
                FROM issues
                WHERE series_id = %s
                ORDER BY issue_number
                LIMIT %s
            """, (serie_id, read_issues))
            
            edicoes = cursor.fetchall()
            
            for issue_id, issue_num, is_read in edicoes:
                if not is_read:  # Só atualizar se não estiver marcada
                    try:
                        cursor.execute("""
                            UPDATE issues
                            SET is_read = TRUE
                            WHERE id = %s
                        """, (issue_id,))
                        total_atualizadas += 1
                        print(f"      ✅ Edição #{issue_num} marcada como lida")
                    except Exception as e:
                        print(f"      ❌ Erro ao atualizar edição #{issue_num}: {e}")
                else:
                    print(f"      ⏭️  Edição #{issue_num} já estava marcada como lida")
        
        series_processadas += 1
        
        # Commit a cada série processada
        try:
            conn.commit()
        except Exception as e:
            print(f"   ❌ Erro ao salvar: {e}")
            conn.rollback()
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   📚 Séries processadas: {series_processadas}")
    print(f"   ✏️  Edições atualizadas (marcadas como lidas): {total_atualizadas}")
    print(f"   ➕ Edições criadas: {total_criadas}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("\n💡 Agora o campo 'Lendo' deve estar sincronizado!")
    print("   Os valores mostrados na aplicação vão refletir os dados da planilha.")
    print("=" * 70)

if __name__ == "__main__":
    try:
        print("\n⚠️  Este script vai:")
        print("   1. Ler o campo 'read_issues' da tabela SERIES")
        print("   2. Marcar as primeiras N edições como lidas na tabela ISSUES")
        print("   3. Se não existirem edições, criar automaticamente")
        print("\n💡 Exemplo:")
        print("   Se Batman tem read_issues = 5")
        print("   → Marca edições #1, #2, #3, #4, #5 como lidas (is_read = TRUE)")
        
        confirmacao = input("\nDeseja continuar? (s/n): ").strip().lower()
        
        if confirmacao in ['s', 'sim', 'y', 'yes']:
            sincronizar_campo_lendo()
        else:
            print("\n❌ Operação cancelada pelo usuário")
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
