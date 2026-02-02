#!/usr/bin/env python3
"""
DIAGNÓSTICO: Comparar Planilha vs Banco
Mostra os dados da planilha e do banco lado a lado para verificar diferenças
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os

# Configuração
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def selecionar_arquivo_excel():
    """Permite ao usuário selecionar qual arquivo Excel analisar"""
    print("=" * 70)
    print("📁 SELEÇÃO DE ARQUIVO")
    print("=" * 70)
    
    arquivos_excel = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    if not arquivos_excel:
        print("\n❌ Nenhum arquivo Excel encontrado!")
        sys.exit(1)
    
    arquivos_excel.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print(f"\n📚 {len(arquivos_excel)} arquivo(s) Excel encontrado(s):\n")
    
    for i, arquivo in enumerate(arquivos_excel, 1):
        tamanho_kb = os.path.getsize(arquivo) / 1024
        data_mod = datetime.fromtimestamp(os.path.getmtime(arquivo))
        data_str = data_mod.strftime('%d/%m/%Y %H:%M')
        
        print(f"  [{i}] {arquivo}")
        print(f"      📅 Modificado: {data_str} | 📊 Tamanho: {tamanho_kb:.1f} KB")
        print()
    
    while True:
        try:
            escolha = input(f"\n👉 Digite o número do arquivo para ANALISAR [1-{len(arquivos_excel)}]: ").strip()
            numero = int(escolha)
            
            if 1 <= numero <= len(arquivos_excel):
                return arquivos_excel[numero - 1]
            else:
                print(f"❌ Número inválido!")
        except ValueError:
            print("❌ Digite apenas números!")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado")
            sys.exit(0)

def diagnosticar(EXCEL_FILE):
    print("\n" + "=" * 70)
    print("🔍 DIAGNÓSTICO: PLANILHA vs BANCO")
    print("=" * 70)
    
    # Ler planilha
    print(f"\n📖 Lendo planilha: {EXCEL_FILE}")
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ {len(df)} linhas encontradas")
        print(f"\n📋 Colunas na planilha:")
        for col in df.columns:
            print(f"   - {col}")
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        sys.exit(1)
    
    # Conectar ao banco
    print("\n🔌 Conectando ao banco...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Buscar dados do banco
    cursor.execute("""
        SELECT id, title, read_issues, downloaded_issues, total_issues
        FROM series
        ORDER BY title
    """)
    banco_data = {row[1].lower().strip(): (row[0], row[2], row[3], row[4]) for row in cursor.fetchall()}
    
    # Comparar
    print("\n" + "=" * 100)
    print("📊 COMPARAÇÃO DETALHADA (primeiras 20 HQs)")
    print("=" * 100)
    print(f"\n{'NOME':<30} | {'PLANILHA (L/B/T)':<20} | {'BANCO (L/B/T)':<20} | STATUS")
    print("-" * 100)
    
    problemas = []
    corretas = 0
    
    for idx, row in df.head(20).iterrows():
        nome = str(row.get('NOME', '')).strip()
        if not nome or nome == 'nan':
            continue
        
        # Dados da planilha
        lendo_plan = row.get('Nº ISSUE LENDO', 'N/A')
        baixado_plan = row.get('Nº BAIXADO', 'N/A')
        total_plan = row.get('TOTAL ISSUES', 'N/A')
        
        # Converter para int se possível
        try:
            lendo_plan = int(lendo_plan) if pd.notna(lendo_plan) else 0
            baixado_plan = int(baixado_plan) if pd.notna(baixado_plan) else 0
            total_plan = int(total_plan) if pd.notna(total_plan) else 0
        except:
            pass
        
        plan_str = f"{lendo_plan}/{baixado_plan}/{total_plan}"
        
        # Dados do banco
        nome_lower = nome.lower().strip()
        if nome_lower in banco_data:
            id_banco, lendo_banco, baixado_banco, total_banco = banco_data[nome_lower]
            banco_str = f"{lendo_banco}/{baixado_banco}/{total_banco}"
            
            # Verificar se são diferentes
            if lendo_plan != lendo_banco or baixado_plan != baixado_banco or total_plan != total_banco:
                status = "⚠️ DIFERENTE"
                problemas.append(nome)
            else:
                status = "✅ OK"
                corretas += 1
        else:
            banco_str = "NÃO ENCONTRADA"
            status = "❌ FALTA"
        
        # Truncar nome se for muito grande
        nome_display = nome[:28] + "..." if len(nome) > 30 else nome
        
        print(f"{nome_display:<30} | {plan_str:<20} | {banco_str:<20} | {status}")
    
    print("\n" + "=" * 100)
    print("📈 RESUMO")
    print("=" * 100)
    print(f"\n✅ HQs corretas (planilha = banco): {corretas}")
    print(f"⚠️  HQs com diferenças: {len(problemas)}")
    
    if problemas:
        print("\n⚠️  HQs que precisam ser atualizadas:")
        for nome in problemas[:10]:
            print(f"   - {nome}")
        if len(problemas) > 10:
            print(f"   ... e mais {len(problemas) - 10}")
    
    # Verificar campos vazios na planilha
    print("\n" + "=" * 100)
    print("🔍 VERIFICAÇÃO DE CAMPOS VAZIOS NA PLANILHA")
    print("=" * 100)
    
    vazios_lendo = df['Nº ISSUE LENDO'].isna().sum()
    vazios_baixado = df['Nº BAIXADO'].isna().sum()
    vazios_total = df['TOTAL ISSUES'].isna().sum()
    
    zeros_lendo = (df['Nº ISSUE LENDO'] == 0).sum()
    zeros_baixado = (df['Nº BAIXADO'] == 0).sum()
    zeros_total = (df['TOTAL ISSUES'] == 0).sum()
    
    print(f"\n📊 Campos VAZIOS (NaN):")
    print(f"   Nº ISSUE LENDO: {vazios_lendo}")
    print(f"   Nº BAIXADO: {vazios_baixado}")
    print(f"   TOTAL ISSUES: {vazios_total}")
    
    print(f"\n📊 Campos com ZERO:")
    print(f"   Nº ISSUE LENDO: {zeros_lendo}")
    print(f"   Nº BAIXADO: {zeros_baixado}")
    print(f"   TOTAL ISSUES: {zeros_total}")
    
    if vazios_lendo > 0 or vazios_baixado > 0 or vazios_total > 0:
        print("\n⚠️  ATENÇÃO: Sua planilha tem campos vazios!")
        print("   Se você importar esta planilha, esses valores serão zerados no banco.")
        print("\n💡 Recomendação:")
        print("   1. Abra a planilha no Excel")
        print("   2. Preencha os campos vazios com os valores corretos")
        print("   3. Salve a planilha")
        print("   4. Execute o script de sincronização novamente")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    try:
        arquivo = selecionar_arquivo_excel()
        diagnosticar(arquivo)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
