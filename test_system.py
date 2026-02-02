"""
Script de Teste - HQ Manager v2.1
Verifica se todas as funcionalidades estão OK
"""

import os
import sqlite3

print("=" * 70)
print("TESTE DE INTEGRIDADE - HQ MANAGER v2.1")
print("=" * 70)

# 1. Verificar arquivos necessários
print("\n1. Verificando arquivos...")
required_files = [
    'main.py',
    'index.html',
    'styles.css',
    'script.js',
    'script-extensions.js',
    'import_planilha_v2.py',
    'export_planilha.py',
    'requirements.txt',
    'README.md'
]

missing_files = []
for file in required_files:
    if os.path.exists(file):
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - FALTANDO")
        missing_files.append(file)

if missing_files:
    print(f"\n⚠️  Arquivos faltando: {', '.join(missing_files)}")
else:
    print("\n✓ Todos os arquivos presentes!")

# 2. Verificar dependências
print("\n2. Verificando dependências...")
try:
    import fastapi
    print("  ✓ fastapi")
except ImportError:
    print("  ✗ fastapi - Execute: pip install fastapi")

try:
    import uvicorn
    print("  ✓ uvicorn")
except ImportError:
    print("  ✗ uvicorn - Execute: pip install uvicorn")

try:
    import pandas
    print("  ✓ pandas")
except ImportError:
    print("  ✗ pandas - Execute: pip install pandas")

try:
    import openpyxl
    print("  ✓ openpyxl")
except ImportError:
    print("  ✗ openpyxl - Execute: pip install openpyxl")

# 3. Verificar banco de dados (se existir)
print("\n3. Verificando banco de dados...")
if os.path.exists('hq_manager.db'):
    conn = sqlite3.connect('hq_manager.db')
    cursor = conn.cursor()
    
    # Verificar tabela series
    cursor.execute("PRAGMA table_info(series)")
    columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = ['id', 'title', 'series_type', 'cover_url']
    missing_cols = [col for col in required_columns if col not in columns]
    
    if missing_cols:
        print(f"  ⚠️  Colunas faltando na tabela series: {', '.join(missing_cols)}")
        print("  → Execute import_planilha_v2.py para atualizar o banco")
    else:
        print("  ✓ Estrutura do banco OK")
        
        # Estatísticas
        cursor.execute("SELECT COUNT(*) FROM series")
        total = cursor.fetchone()[0]
        print(f"  ℹ️  Total de séries: {total}")
        
        if total > 0:
            cursor.execute("SELECT COUNT(*) FROM series WHERE series_type IS NOT NULL")
            with_type = cursor.fetchone()[0]
            print(f"  ℹ️  Séries com tipo definido: {with_type}")
            
            cursor.execute("SELECT COUNT(*) FROM series WHERE cover_url IS NOT NULL AND cover_url != ''")
            with_cover = cursor.fetchone()[0]
            print(f"  ℹ️  Séries com capa: {with_cover}")
    
    conn.close()
else:
    print("  ℹ️  Banco de dados ainda não criado")
    print("  → Execute import_planilha_v2.py para criar")

# 4. Verificar planilha (se existir)
print("\n4. Verificando planilha...")
if os.path.exists('Planilha_de_HQs.xlsx'):
    try:
        import pandas as pd
        df = pd.read_excel('Planilha_de_HQs.xlsx')
        print(f"  ✓ Planilha encontrada com {len(df)} HQs")
        print(f"  ℹ️  Colunas: {df.columns.tolist()}")
        
        # Verificar coluna TIPO
        if 'TIPO' in df.columns:
            print("  ✓ Coluna TIPO presente")
            tipos = df['TIPO'].value_counts()
            print("  📊 Distribuição por tipo:")
            for tipo, count in tipos.items():
                if pd.notna(tipo):
                    print(f"     {tipo}: {count}")
        else:
            print("  ⚠️  Coluna TIPO não encontrada")
            print("  → Adicione manualmente ou será definida como 'Em andamento'")
        
        # Verificar coluna CAPA
        if 'CAPA' in df.columns:
            with_cover = df['CAPA'].notna().sum()
            print(f"  ✓ Coluna CAPA presente ({with_cover} HQs com capa)")
        else:
            print("  ⚠️  Coluna CAPA não encontrada")
            print("  → Adicione para importar URLs de capas")
    except Exception as e:
        print(f"  ✗ Erro ao ler planilha: {e}")
else:
    print("  ℹ️  Planilha não encontrada")
    print("  → Crie Planilha_de_HQs.xlsx com as colunas necessárias")

# Resumo final
print("\n" + "=" * 70)
print("RESUMO DO TESTE")
print("=" * 70)

if not missing_files:
    print("✅ Sistema pronto para uso!")
    print("\n📝 Próximos passos:")
    print("   1. Se ainda não importou: python import_planilha_v2.py")
    print("   2. Iniciar backend: python main.py")
    print("   3. Iniciar frontend: python -m http.server 8080")
    print("   4. Acessar: http://localhost:8080")
else:
    print("⚠️  Sistema incompleto - verifique os arquivos faltando")

print("=" * 70)
