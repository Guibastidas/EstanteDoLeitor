#!/usr/bin/env python3
"""
IMPORTAÇÃO DIRETA: Excel → PostgreSQL Railway
Importa a planilha diretamente para o banco, sem migração
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os

DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"
EXCEL_FILE = "Planilha_de_HQs.xlsx"

def importar_excel():
    print("=" * 70)
    print("📚 IMPORTAÇÃO DIRETA: EXCEL → RAILWAY")
    print("=" * 70)
    
    # Verificar arquivo
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ Arquivo não encontrado: {EXCEL_FILE}")
        print("\nArquivos disponíveis:")
        for f in os.listdir('.'):
            if f.endswith(('.xlsx', '.xls')):
                print(f"  - {f}")
        sys.exit(1)
    
    print(f"\n📖 Lendo planilha: {EXCEL_FILE}")
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ {len(df)} linhas encontradas")
        print(f"\nColunas: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        sys.exit(1)
    
    # Conectar ao PostgreSQL
    print("\n🔌 Conectando ao Railway...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Verificar se já existem dados
    cursor.execute("SELECT COUNT(*) FROM series;")
    count_existing = cursor.fetchone()[0]
    
    if count_existing > 0:
        print(f"\n⚠️  Já existem {count_existing} HQs no banco!")
        print("\n   Você deve primeiro executar: python limpar_railway.py")
        conn.close()
        sys.exit(1)
    
    # Importar
    print("\n📚 Importando HQs...")
    print("-" * 70)
    
    imported = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            # Ler dados da linha
            nome = str(row.get('NOME', '')).strip()
            if not nome or nome == 'nan':
                continue
            
            autor = row.get('AUTOR', None)
            if pd.isna(autor) or str(autor).strip() == '':
                autor = None
            else:
                autor = str(autor).strip()
            
            editora = row.get('EDITORA', None)
            if pd.isna(editora) or str(editora).strip() == '':
                editora = None
            else:
                editora = str(editora).strip()
            
            # Números
            lendo = int(row.get('Nº ISSUE LENDO', 0)) if pd.notna(row.get('Nº ISSUE LENDO')) else 0
            baixado = int(row.get('Nº BAIXADO', lendo)) if pd.notna(row.get('Nº BAIXADO')) else lendo
            total = int(row.get('TOTAL ISSUES', baixado)) if pd.notna(row.get('TOTAL ISSUES')) else baixado
            
            # Tipo
            tipo_excel = str(row.get('TIPO', 'Em andamento'))
            tipo_map = {
                'Finalizada': 'finalizada',
                'Em andamento': 'em_andamento',
                'Lançamento': 'lancamento',
                'Edição Especial': 'edicao_especial'
            }
            tipo = tipo_map.get(tipo_excel, 'em_andamento')
            
            # Finalizada
            finalizada_excel = str(row.get('FINALIZADA', 'Não'))
            is_completed = finalizada_excel.lower() in ['sim', 'true', '1']
            
            # Capa e notas
            capa = row.get('CAPA', None)
            if pd.isna(capa) or str(capa).strip() == '':
                capa = None
            else:
                capa = str(capa).strip()
            
            notas = row.get('NOTAS', None)
            if pd.isna(notas) or str(notas).strip() == '':
                notas = None
            else:
                notas = str(notas).strip()
            
            # Data
            date_added = datetime.now().isoformat()
            
            # Inserir no banco
            cursor.execute("""
                INSERT INTO series (
                    title, author, publisher, 
                    read_issues, downloaded_issues, total_issues,
                    is_completed, series_type,
                    cover_url, notes, date_added
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nome, autor, editora,
                lendo, baixado, total,
                is_completed, tipo,
                capa, notas, date_added
            ))
            
            imported += 1
            
            if imported % 10 == 0:
                print(f"  ✅ {imported} HQs importadas...")
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Erro na linha {idx + 1} ({nome}): {e}")
    
    # Commit
    try:
        conn.commit()
        print(f"\n✅ Commit realizado!")
    except Exception as e:
        print(f"\n❌ Erro ao fazer commit: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    # Verificar resultado
    cursor.execute("SELECT COUNT(*) FROM series;")
    total_final = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("🎉 IMPORTAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   ✅ Importadas: {imported}")
    print(f"   ❌ Erros: {errors}")
    print(f"   📚 Total no banco: {total_final}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("=" * 70)

if __name__ == "__main__":
    try:
        importar_excel()
    except KeyboardInterrupt:
        print("\n\n❌ Importação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
