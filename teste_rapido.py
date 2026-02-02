"""
Teste Rápido - Verificar se API está funcionando
"""

import sqlite3
import sys

print("=" * 70)
print("TESTE RÁPIDO DO SISTEMA")
print("=" * 70)

# 1. Verificar banco
print("\n1️⃣  Verificando banco de dados...")
try:
    conn = sqlite3.connect('hq_manager.db')
    cursor = conn.cursor()
    
    # Verificar se tem tabela series
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='series'")
    if cursor.fetchone():
        print("   ✓ Tabela 'series' encontrada")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM series")
        total = cursor.fetchone()[0]
        print(f"   ✓ {total} séries no banco")
        
        if total > 0:
            # Mostrar primeira série
            cursor.execute("SELECT title, read_issues, total_issues FROM series LIMIT 1")
            row = cursor.fetchone()
            print(f"   📖 Exemplo: '{row[0]}' - {row[1]}/{row[2]} lidas")
        else:
            print("   ⚠️  Banco vazio!")
            print("   → Execute: python importar_planilha.py")
            sys.exit(1)
    else:
        print("   ❌ Tabela 'series' não encontrada!")
        print("   → Execute: python importar_planilha.py")
        sys.exit(1)
    
    conn.close()
except Exception as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# 2. Testar API
print("\n2️⃣  Testando API...")
try:
    import requests
    
    # Tentar conectar à API
    try:
        response = requests.get('http://localhost:8000/', timeout=2)
        print("   ✓ API está rodando!")
        print(f"   → {response.json()}")
    except requests.exceptions.ConnectionError:
        print("   ⚠️  API não está rodando")
        print("   → Execute: python main.py")
        print("\n   Testando estrutura sem API...")
        
        # Simular resposta da API
        conn = sqlite3.connect('hq_manager.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN read_issues = 0 THEN 1 ELSE 0 END) as para_ler,
                   SUM(CASE WHEN read_issues > 0 AND read_issues < total_issues THEN 1 ELSE 0 END) as lendo,
                   SUM(CASE WHEN read_issues >= total_issues AND total_issues > 0 THEN 1 ELSE 0 END) as concluidas
            FROM series
        """)
        
        stats = cursor.fetchone()
        print(f"\n   📊 Estatísticas (do banco):")
        print(f"      Total: {stats[0]}")
        print(f"      Para Ler: {stats[1]}")
        print(f "      Lendo: {stats[2]}")
        print(f"      Concluídas: {stats[3]}")
        
        conn.close()
        
    # Testar endpoint de stats
    try:
        response = requests.get('http://localhost:8000/stats', timeout=2)
        stats = response.json()
        print(f"\n   📊 Estatísticas (da API):")
        print(f"      Total: {stats['total']}")
        print(f"      Para Ler: {stats['para_ler']}")
        print(f"      Lendo: {stats['lendo']}")
        print(f"      Concluídas: {stats['concluidas']}")
    except:
        pass
        
except ImportError:
    print("   ⚠️  Biblioteca 'requests' não instalada")
    print("   → Instale: pip install requests")
    print("   → Mas o sistema pode funcionar sem ela")

# 3. Verificar arquivos
print("\n3️⃣  Verificando arquivos...")
import os

arquivos_necessarios = {
    'main.py': True,
    'index.html': True,
    'script.js': True,
    'styles.css': True
}

todos_ok = True
for arquivo, obrigatorio in arquivos_necessarios.items():
    if os.path.exists(arquivo):
        print(f"   ✓ {arquivo}")
    else:
        if obrigatorio:
            print(f"   ❌ {arquivo} (obrigatório!)")
            todos_ok = False
        else:
            print(f"   ⚠️  {arquivo} (opcional)")

if not todos_ok:
    print("\n   ❌ Arquivos faltando!")
    sys.exit(1)

# CONCLUSÃO
print("\n" + "=" * 70)
if total > 0:
    print("✅ SISTEMA OK!")
    print("\n🚀 Próximos passos:")
    print("   1. Execute: python main.py")
    print("   2. Abra index.html no navegador")
    print("   3. Ou acesse: http://localhost:8080 (se usar: python -m http.server 8080)")
else:
    print("⚠️  SISTEMA OK MAS BANCO VAZIO")
    print("\n🚀 Próximos passos:")
    print("   1. Execute: python importar_planilha.py")
    print("   2. Execute: python main.py")
    print("   3. Abra index.html no navegador")

print("=" * 70)
