#!/usr/bin/env python3
"""
EXPORTAÇÃO: PostgreSQL Railway → Excel
Exporta todas as HQs do banco para uma planilha Excel
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os

# Configuração do banco (Railway)
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

# Nome do arquivo de saída
OUTPUT_FILE = f"Planilha_HQs_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

def exportar_para_excel():
    print("=" * 70)
    print("📤 EXPORTAÇÃO: RAILWAY → EXCEL")
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
    print("\n📚 Buscando HQs no banco...")
    try:
        cursor.execute("""
            SELECT 
                id,
                title,
                author,
                publisher,
                read_issues,
                downloaded_issues,
                total_issues,
                is_completed,
                series_type,
                cover_url,
                notes,
                date_added,
                date_updated
            FROM series
            ORDER BY title
        """)
        
        rows = cursor.fetchall()
        print(f"✅ {len(rows)} HQs encontradas")
        
    except Exception as e:
        print(f"❌ Erro ao buscar dados: {e}")
        conn.close()
        sys.exit(1)
    
    # Converter para DataFrame
    print("\n📊 Convertendo para Excel...")
    
    data = []
    for row in rows:
        # Mapeamento de tipos
        tipo_map = {
            'finalizada': 'Finalizada',
            'em_andamento': 'Em andamento',
            'lancamento': 'Lançamento',
            'edicao_especial': 'Edição Especial'
        }
        
        tipo_excel = tipo_map.get(row[8], 'Em andamento')
        finalizada_excel = 'Sim' if row[7] else 'Não'
        
        data.append({
            'ID': row[0],
            'NOME': row[1],
            'AUTOR': row[2] or '',
            'EDITORA': row[3] or '',
            'Nº ISSUE LENDO': row[4],
            'Nº BAIXADO': row[5],
            'TOTAL ISSUES': row[6],
            'FINALIZADA': finalizada_excel,
            'TIPO': tipo_excel,
            'CAPA': row[9] or '',
            'NOTAS': row[10] or '',
            'DATA ADICIONADA': row[11],
            'DATA ATUALIZADA': row[12] or ''
        })
    
    df = pd.DataFrame(data)
    
    # Salvar Excel
    try:
        df.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')
        print(f"✅ Arquivo criado: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Erro ao criar Excel: {e}")
        conn.close()
        sys.exit(1)
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ EXPORTAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   📁 Arquivo: {OUTPUT_FILE}")
    print(f"   📚 Total de HQs: {len(data)}")
    print("\n💡 Agora você pode:")
    print("   1. Editar a planilha no Excel")
    print("   2. Importar de volta usando: python importar_atualizado.py")
    print("=" * 70)

if __name__ == "__main__":
    try:
        exportar_para_excel()
    except KeyboardInterrupt:
        print("\n\n❌ Exportação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
