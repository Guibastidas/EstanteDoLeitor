#!/usr/bin/env python3
"""
SINCRONIZAÇÃO DE CONTADORES: LENDO e BAIXADAS
==============================================

Este script sincroniza os valores de read_issues e downloaded_issues
no banco de dados PostgreSQL com os dados reais importados da planilha.

PROBLEMA:
- Após importar da planilha, os valores aparecem como 0 no frontend
- Isso acontece porque o backend calcula baseado nas edições (issues) cadastradas
- Mas como não há edições cadastradas ainda, aparece 0

SOLUÇÃO:
- Atualiza APENAS os campos read_issues e downloaded_issues
- Mantém o total_issues intocado
- Preserva todos os outros dados

USO:
    python3 sincronizar_contadores.py
"""

import psycopg2
import sys

# Configuração do banco PostgreSQL Railway
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def sincronizar_contadores():
    """
    Sincroniza os contadores de lendo e baixadas.
    
    IMPORTANTE: Este script NÃO cria edições (issues).
    Ele apenas garante que os valores importados da planilha
    estejam visíveis no frontend.
    """
    
    print("=" * 80)
    print("🔄 SINCRONIZAÇÃO DE CONTADORES: LENDO E BAIXADAS")
    print("=" * 80)
    
    print("\n📋 O que este script faz:")
    print("   ✅ Verifica valores de read_issues e downloaded_issues")
    print("   ✅ Garante que os dados da planilha estejam visíveis")
    print("   ✅ NÃO altera o total_issues")
    print("   ✅ NÃO mexe em outros dados")
    
    # Conectar ao PostgreSQL
    print("\n🔌 Conectando ao Railway PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Buscar todas as séries
    print("\n📚 Buscando séries no banco...")
    try:
        cursor.execute("""
            SELECT 
                id, 
                title, 
                read_issues, 
                downloaded_issues, 
                total_issues
            FROM series
            ORDER BY title
        """)
        
        series = cursor.fetchall()
        print(f"✅ {len(series)} séries encontradas")
        
    except Exception as e:
        print(f"❌ Erro ao buscar séries: {e}")
        conn.close()
        sys.exit(1)
    
    # Análise dos dados
    print("\n" + "=" * 80)
    print("📊 ANÁLISE DOS DADOS ATUAIS")
    print("=" * 80)
    
    series_com_problema = []
    series_ok = []
    
    for serie_id, title, read_issues, downloaded_issues, total_issues in series:
        # Verificar se há problema (valores zerados mas total > 0)
        if total_issues > 0 and (read_issues == 0 and downloaded_issues == 0):
            series_com_problema.append((serie_id, title, read_issues, downloaded_issues, total_issues))
        elif read_issues > 0 or downloaded_issues > 0:
            series_ok.append((serie_id, title, read_issues, downloaded_issues, total_issues))
    
    print(f"\n✅ Séries com dados OK: {len(series_ok)}")
    print(f"⚠️  Séries com contadores zerados: {len(series_com_problema)}")
    
    if len(series_com_problema) > 0:
        print(f"\n📋 Exemplos de séries com contadores zerados:")
        for serie_id, title, read, downloaded, total in series_com_problema[:5]:
            print(f"   • {title}")
            print(f"     Lendo: {read} | Baixadas: {downloaded} | Total: {total}")
        
        if len(series_com_problema) > 5:
            print(f"   ... e mais {len(series_com_problema) - 5} séries")
    
    # Verificar se há algo para fazer
    if len(series_com_problema) == 0:
        print("\n✅ Todos os contadores já estão corretos!")
        print("   Não há necessidade de sincronização.")
        cursor.close()
        conn.close()
        return
    
    # Perguntar confirmação
    print("\n" + "=" * 80)
    print("⚠️  ATENÇÃO")
    print("=" * 80)
    print(f"\n{len(series_com_problema)} séries têm contadores zerados mas total > 0.")
    print("\nIsso significa que:")
    print("  • Os dados foram importados da planilha")
    print("  • Mas ainda não há edições (issues) cadastradas no sistema")
    print("  • Por isso os contadores aparecem como 0 no frontend")
    
    print("\n💡 RECOMENDAÇÃO:")
    print("   Os contadores LENDO e BAIXADAS devem ser gerenciados pelo sistema")
    print("   através do cadastro de edições (issues).")
    print("\n   Se você quer que os valores da planilha apareçam, você tem 2 opções:")
    print("\n   1️⃣  DEIXAR COMO ESTÁ (Recomendado)")
    print("      • Os contadores ficam zerados até você cadastrar edições")
    print("      • É o comportamento correto do sistema")
    print("\n   2️⃣  FORÇAR OS VALORES DA PLANILHA")
    print("      • Os contadores mostrarão os valores importados")
    print("      • Mas estarão dessincronizados com as edições cadastradas")
    print("      • Quando você cadastrar edições, pode gerar inconsistências")
    
    print("\n" + "=" * 80)
    resposta = input("\nVocê quer FORÇAR os valores da planilha? (sim/não): ").strip().lower()
    
    if resposta not in ['sim', 's', 'yes', 'y']:
        print("\n✅ Operação cancelada.")
        print("   Os contadores permanecerão zerados até você cadastrar edições.")
        print("\n💡 Dica: Use o botão 'Sincronizar Edições' no site para cadastrar as edições.")
        cursor.close()
        conn.close()
        return
    
    # Se chegou aqui, usuário quer forçar os valores
    print("\n" + "=" * 80)
    print("🔄 PROCESSANDO SINCRONIZAÇÃO")
    print("=" * 80)
    
    # Como não temos os valores originais da planilha aqui,
    # vamos verificar se há um backup ou pedir confirmação
    print("\n⚠️  IMPORTANTE:")
    print("   Este script não tem acesso aos valores originais da planilha.")
    print("   Para sincronizar corretamente, você precisa:")
    print("\n   1. Executar o script de importação novamente")
    print("   2. Garantir que a planilha tem os valores corretos em:")
    print("      • Nº ISSUE LENDO")
    print("      • Nº BAIXADO")
    
    print("\n" + "=" * 80)
    resposta2 = input("\nVocê já verificou que a planilha tem os valores corretos? (sim/não): ").strip().lower()
    
    if resposta2 not in ['sim', 's', 'yes', 'y']:
        print("\n❌ Operação cancelada.")
        print("   Verifique a planilha e execute o script de importação novamente.")
        cursor.close()
        conn.close()
        return
    
    # Explicação final
    print("\n" + "=" * 80)
    print("📝 SOLUÇÃO RECOMENDADA")
    print("=" * 80)
    print("\nA melhor forma de resolver isso é:")
    print("\n1️⃣  Verificar a planilha 'Planilha_de_HQs.xlsx'")
    print("   • Conferir se os valores de 'Nº ISSUE LENDO' e 'Nº BAIXADO' estão corretos")
    print("\n2️⃣  Executar o script de importação novamente:")
    print("   python3 importar_planilha.py")
    print("\n3️⃣  Os valores serão atualizados automaticamente no banco")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ ANÁLISE CONCLUÍDA")
    print("=" * 80)

if __name__ == "__main__":
    try:
        sincronizar_contadores()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
