#!/usr/bin/env python3
"""
Script para LIMPAR COMPLETAMENTE o banco PostgreSQL no Railway
Remove TODAS as HQs e edições
"""

import psycopg2
import sys

DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def limpar_banco():
    print("=" * 70)
    print("🗑️  LIMPEZA COMPLETA DO BANCO RAILWAY")
    print("=" * 70)
    
    print("\n⚠️  ATENÇÃO: Isso vai DELETAR TUDO!")
    print("   - Todas as HQs")
    print("   - Todas as edições")
    print("   - Não há como desfazer!")
    
    confirma = input("\nDigite 'CONFIRMAR' para continuar: ").strip()
    
    if confirma != "CONFIRMAR":
        print("❌ Operação cancelada.")
        return
    
    try:
        print("\n🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Deletar todas as edições primeiro (por causa da foreign key)
        print("🗑️  Deletando edições...")
        cursor.execute("DELETE FROM issues;")
        issues_deleted = cursor.rowcount
        print(f"   ✅ {issues_deleted} edições deletadas")
        
        # Deletar todas as séries
        print("🗑️  Deletando séries...")
        cursor.execute("DELETE FROM series;")
        series_deleted = cursor.rowcount
        print(f"   ✅ {series_deleted} séries deletadas")
        
        # Resetar os IDs
        print("🔄 Resetando sequências de IDs...")
        cursor.execute("ALTER SEQUENCE series_id_seq RESTART WITH 1;")
        cursor.execute("ALTER SEQUENCE issues_id_seq RESTART WITH 1;")
        print("   ✅ IDs resetados")
        
        # Commit
        conn.commit()
        print("\n✅ BANCO LIMPO COM SUCESSO!")
        print(f"   📊 {series_deleted} séries removidas")
        print(f"   📊 {issues_deleted} edições removidas")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🎯 Agora você pode importar do zero!")
    print("   Execute: python importar_para_railway.py")
    print("=" * 70)

if __name__ == "__main__":
    try:
        limpar_banco()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
