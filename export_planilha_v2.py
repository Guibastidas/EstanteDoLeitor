"""
Script de Exportação v2 - Banco de Dados → Planilha
Exporta TODOS os campos do banco de volta para a planilha
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os
import shutil

# Configurações
EXCEL_FILE = 'Planilha_de_HQs.xlsx'
BACKUP_FILE = f'Planilha_de_HQs_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
DB_PATH = 'hq_manager.db'

def export_to_excel():
    """Exporta dados do banco para Excel"""
    
    print("=" * 70)
    print("EXPORTAÇÃO PARA PLANILHA v2.0")
    print("=" * 70)
    
    # Verificar se banco existe
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Banco de dados não encontrado: {DB_PATH}")
        return
    
    # Fazer backup da planilha existente
    if os.path.exists(EXCEL_FILE):
        print(f"\n📦 Criando backup: {BACKUP_FILE}")
        shutil.copy2(EXCEL_FILE, BACKUP_FILE)
        print(f"✓ Backup criado!")
    
    # Conectar ao banco
    conn = sqlite3.connect(DB_PATH)
    
    # Ler dados das séries com TODOS os campos
    print("\n📖 Lendo dados do banco...")
    df = pd.read_sql_query("""
        SELECT 
            title as 'NOME',
            author as 'AUTOR',
            publisher as 'EDITORA',
            read_issues as 'Nº ISSUE LENDO',
            downloaded_issues as 'Nº BAIXADO',
            total_issues as 'TOTAL ISSUES',
            is_completed as 'FINALIZADA',
            CASE series_type
                WHEN 'finalizada' THEN 'Finalizada'
                WHEN 'em_andamento' THEN 'Em andamento'
                WHEN 'lancamento' THEN 'Lançamento'
                WHEN 'edicao_especial' THEN 'Edição Especial'
                ELSE 'Em andamento'
            END as 'TIPO',
            cover_url as 'CAPA',
            notes as 'NOTAS',
            date_added as 'DATA_ADICIONADA',
            date_updated as 'DATA_ATUALIZADA'
        FROM series
        ORDER BY title
    """, conn)
    
    conn.close()
    
    # Substituir None por string vazia para melhor visualização
    df = df.fillna('')
    
    # Converter booleanos para texto legível
    df['FINALIZADA'] = df['FINALIZADA'].apply(lambda x: 'Sim' if x == 1 or x == True else 'Não' if x == 0 or x == False else '')
    
    # Exportar para Excel
    print(f"\n💾 Exportando {len(df)} séries para {EXCEL_FILE}...")
    
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='HQs')
        
        # Ajustar largura das colunas
        worksheet = writer.sheets['HQs']
        col_widths = {
            'NOME': 40,
            'AUTOR': 30,
            'EDITORA': 25,
            'Nº ISSUE LENDO': 15,
            'Nº BAIXADO': 15,
            'TOTAL ISSUES': 15,
            'FINALIZADA': 12,
            'TIPO': 18,
            'CAPA': 60,
            'NOTAS': 40,
            'DATA_ADICIONADA': 20,
            'DATA_ATUALIZADA': 20
        }
        
        for idx, col in enumerate(df.columns):
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            width = col_widths.get(col, 15)
            worksheet.column_dimensions[col_letter].width = width
    
    print(f"✓ Planilha exportada com sucesso!")
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ EXPORTAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"📊 Estatísticas:")
    print(f"   Total de séries exportadas: {len(df)}")
    print(f"   Arquivo: {EXCEL_FILE}")
    print(f"   Backup: {BACKUP_FILE}")
    
    # Contagem por tipo
    if 'TIPO' in df.columns:
        print(f"\n📚 Por tipo:")
        for tipo, count in df['TIPO'].value_counts().items():
            if tipo:
                print(f"   {tipo}: {count}")
    
    print(f"\n📋 Colunas exportadas ({len(df.columns)} colunas):")
    for col in df.columns:
        print(f"   - {col}")
    
    print("\n💡 Agora você pode:")
    print("   1. Abrir e editar a planilha Excel")
    print("   2. Modificar: NOME, EDITORA, TIPO, CAPA, NOTAS, etc.")
    print("   3. Executar: python import_planilha_v2.py")
    print("   4. Suas alterações serão sincronizadas!")
    
    print("\n⚠️  Importante:")
    print("   - As colunas DATA_* são para controle interno")
    print("   - Você pode deletar essas colunas se quiser")
    print("   - Novas HQs podem ser adicionadas manualmente")
    print("   - Todos os campos são opcionais, exceto NOME")
    print("=" * 70)

if __name__ == "__main__":
    try:
        export_to_excel()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
