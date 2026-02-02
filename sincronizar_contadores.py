#!/usr/bin/env python3
"""
Script para RECALCULAR e SINCRONIZAR os contadores do banco
Corrige discrepâncias entre os contadores e as issues reais
"""

import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway")

def sincronizar_contadores():
    print("=" * 70)
    print("🔄 SINCRONIZAÇÃO DE CONTADORES")
    print("=" * 70)
    
    try:
        print("\n🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
        
        # Buscar todas as séries
        cursor.execute("SELECT id, title FROM series ORDER BY id;")
        series = cursor.fetchall()
        
        print(f"\n📚 {len(series)} séries encontradas")
        print("-" * 70)
        
        corrigidas = 0
        
        for series_id, title in series:
            # Contar issues REAIS
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_baixado,
                    COUNT(CASE WHEN is_read = true THEN 1 END) as total_lido
                FROM issues 
                WHERE series_id = %s
            """, (series_id,))
            
            result = cursor.fetchone()
            total_baixado_real = result[0]
            total_lido_real = result[1]
            
            # Buscar valores ATUAIS do banco
            cursor.execute("""
                SELECT downloaded_issues, read_issues, total_issues 
                FROM series 
                WHERE id = %s
            """, (series_id,))
            
            current = cursor.fetchone()
            downloaded_atual = current[0]
            read_atual = current[1]
            total_issues = current[2]
            
            # Verificar se precisa corrigir
            if downloaded_atual != total_baixado_real or read_atual != total_lido_real:
                print(f"\n⚠️  {title} (ID: {series_id})")
                print(f"   ANTES:")
                print(f"   ├─ Lendo: {read_atual} | Baixadas: {downloaded_atual} | Total: {total_issues}")
                print(f"   REAL (contando issues):")
                print(f"   ├─ Lido: {total_lido_real} | Baixado: {total_baixado_real}")
                
                # Atualizar
                cursor.execute("""
                    UPDATE series 
                    SET downloaded_issues = %s, read_issues = %s
                    WHERE id = %s
                """, (total_baixado_real, total_lido_real, series_id))
                
                print(f"   DEPOIS:")
                print(f"   └─ Lendo: {total_lido_real} | Baixadas: {total_baixado_real} | Total: {total_issues}")
                
                corrigidas += 1
        
        # Commit
        conn.commit()
        print("\n" + "=" * 70)
        print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print(f"\n📊 Resultado:")
        print(f"   Total de séries: {len(series)}")
        print(f"   Séries corrigidas: {corrigidas}")
        print(f"   Séries já corretas: {len(series) - corrigidas}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        sincronizar_contadores()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
