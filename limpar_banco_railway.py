"""
Script para limpar o banco de dados PostgreSQL no Railway
Apaga todas as tabelas e recomeça do zero
"""

import os
import sys

print("=" * 70)
print("LIMPEZA DO BANCO DE DADOS POSTGRESQL")
print("=" * 70)

# Verificar DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("\n❌ DATABASE_URL não encontrada!")
    print("   Configure: $env:DATABASE_URL='sua_url_aqui'")
    sys.exit(1)

# Corrigir URL se necessário
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("\n⚠️  ATENÇÃO: Este script vai APAGAR TODAS AS TABELAS!")
print("   - Tabela 'comics' e todos os dados serão perdidos")
print("   - Isso não pode ser desfeito!")

resposta = input("\n❓ Tem certeza que deseja continuar? (digite 'SIM' para confirmar): ")

if resposta.upper() != "SIM":
    print("\n✅ Operação cancelada. Nenhum dado foi apagado.")
    sys.exit(0)

print("\n🔌 Conectando ao PostgreSQL...")

try:
    from sqlalchemy import create_engine, text
    
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
    print("✅ Conectado!")
    
    with engine.connect() as conn:
        print("\n🗑️  Apagando tabelas...")
        
        # Apagar tabela comics
        conn.execute(text("DROP TABLE IF EXISTS comics CASCADE"))
        conn.commit()
        
        print("✅ Tabela 'comics' apagada!")
        
        # Verificar se há outras tabelas
        result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        
        tabelas = result.fetchall()
        
        if tabelas:
            print(f"\n📊 Outras tabelas encontradas: {len(tabelas)}")
            for tabela in tabelas:
                print(f"   - {tabela[0]}")
            
            apagar_todas = input("\n❓ Apagar TODAS as tabelas também? (s/n): ")
            
            if apagar_todas.lower() == 's':
                for tabela in tabelas:
                    conn.execute(text(f"DROP TABLE IF EXISTS {tabela[0]} CASCADE"))
                    print(f"   🗑️  {tabela[0]} apagada")
                conn.commit()
                print("\n✅ Todas as tabelas apagadas!")
        else:
            print("\n✅ Nenhuma outra tabela encontrada")
    
    print("\n" + "=" * 70)
    print("🎉 LIMPEZA CONCLUÍDA!")
    print("=" * 70)
    print("\n💡 Próximos passos:")
    print("   1. Execute: python import_excel_to_railway.py")
    print("   2. Suas HQs serão importadas em um banco limpo")
    print("=" * 70)
    
except ImportError:
    print("❌ sqlalchemy não encontrado. Instale: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
