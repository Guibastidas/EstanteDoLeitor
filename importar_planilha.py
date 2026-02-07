#!/usr/bin/env python3
"""
IMPORTAÇÃO INTELIGENTE: Excel → PostgreSQL Railway
==================================================

Este script importa HQs da planilha Excel para o banco PostgreSQL Railway.

CARACTERÍSTICAS:
- Evita duplicação de HQs (usa o NOME como chave única)
- Atualiza HQs existentes sem perder dados
- Valida e ajusta os valores de LENDO, BAIXADO e TOTAL ISSUES
- Mantém integridade dos dados (lendo ≤ baixado ≤ total)
- Commit incremental para evitar perda de dados em caso de erro

MAPEAMENTO DE CAMPOS:
Planilha Excel          → Banco de Dados
-------------------------------------------------
NOME                    → series.title
AUTOR                   → series.author
EDITORA                 → series.publisher
Nº ISSUE LENDO          → series.read_issues
Nº BAIXADO              → series.downloaded_issues
TOTAL ISSUES            → series.total_issues
FINALIZADA (Sim/Não)    → series.is_completed (boolean)
TIPO                    → series.series_type
CAPA                    → series.cover_url
NOTAS                   → series.notes

USO:
1. Coloque este script na mesma pasta da planilha "Planilha_de_HQs.xlsx"
2. Execute: python3 importar_planilha.py
3. Acompanhe o progresso no terminal
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os

# ==================== CONFIGURAÇÕES ====================

# Configuração do banco PostgreSQL Railway
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

# Nome do arquivo da planilha (deve estar na mesma pasta do script)
EXCEL_FILE = "Planilha_de_HQs.xlsx"

# Número de registros por commit (para evitar perda de dados)
COMMIT_BATCH_SIZE = 20

# ==================== FUNÇÕES AUXILIARES ====================

def normalizar_titulo(titulo):
    """
    Normaliza título para comparação (remove espaços extras, converte para minúsculas).
    Isso evita duplicação de HQs com nomes ligeiramente diferentes.
    
    Exemplos:
    "Batman" e "batman" são considerados iguais
    "Spider-Man " e "Spider-Man" são considerados iguais
    """
    if not titulo or pd.isna(titulo):
        return ""
    return str(titulo).strip().lower()


def validar_e_ajustar_numeros(lendo, baixado, total):
    """
    Valida e ajusta os números para manter integridade:
    - read_issues (lendo) não pode ser maior que downloaded_issues (baixado)
    - downloaded_issues (baixado) não pode ser maior que total_issues (total)
    
    Retorna: (lendo_ajustado, baixado_ajustado, total_ajustado)
    """
    # Garantir valores não negativos
    lendo = max(0, int(lendo) if pd.notna(lendo) else 0)
    baixado = max(0, int(baixado) if pd.notna(baixado) else 0)
    total = max(0, int(total) if pd.notna(total) else 0)
    
    # Ajustar hierarquia: lendo ≤ baixado ≤ total
    lendo = min(lendo, baixado)
    baixado = min(baixado, total)
    
    return lendo, baixado, total


def mapear_tipo_serie(tipo_excel):
    """
    Mapeia tipo da planilha para o formato do banco.
    
    Planilha → Banco:
    "Finalizada"        → "finalizada"
    "Em andamento"      → "em_andamento"
    "Lançamento"        → "lancamento"
    "Edição Especial"   → "edicao_especial"
    """
    tipo_map = {
        'finalizada': 'finalizada',
        'em andamento': 'em_andamento',
        'lançamento': 'lancamento',
        'lancamento': 'lancamento',  # sem acento também
        'edição especial': 'edicao_especial',
        'edicao especial': 'edicao_especial',  # sem acento também
    }
    
    tipo_norm = str(tipo_excel).strip().lower()
    return tipo_map.get(tipo_norm, 'em_andamento')


def mapear_finalizada(finalizada_excel):
    """
    Converte valor de FINALIZADA para boolean.
    
    Aceita: "Sim", "sim", "Yes", "yes", "True", "true", "1"
    Qualquer outro valor retorna False
    """
    if pd.isna(finalizada_excel):
        return False
    
    valor_norm = str(finalizada_excel).strip().lower()
    return valor_norm in ['sim', 'yes', 'true', '1']

def importar_planilha():
    print("=" * 80)
    print("📚 IMPORTAÇÃO INTELIGENTE: PLANILHA → RAILWAY")
    print("=" * 80)
    
    # Verificar se arquivo existe
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ Erro: Arquivo '{EXCEL_FILE}' não encontrado!")
        print("💡 Certifique-se de que a planilha está na mesma pasta do script.")
        sys.exit(1)
    
    # Ler planilha
    print(f"\n📖 Lendo planilha: {EXCEL_FILE}")
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ {len(df)} linhas encontradas")
        print(f"\n📊 Colunas: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        sys.exit(1)
    
    # Validar colunas obrigatórias
    colunas_esperadas = ['NOME', 'AUTOR', 'EDITORA', 'Nº ISSUE LENDO', 'Nº BAIXADO', 
                         'TOTAL ISSUES', 'FINALIZADA', 'TIPO', 'CAPA', 'NOTAS']
    colunas_faltando = [col for col in colunas_esperadas if col not in df.columns]
    
    if colunas_faltando:
        print(f"\n⚠️  Aviso: Colunas faltando na planilha: {colunas_faltando}")
    
    # Conectar ao PostgreSQL
    print("\n🔌 Conectando ao Railway PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Buscar HQs existentes no banco
    print("\n🔍 Verificando HQs existentes no banco...")
    try:
        cursor.execute("SELECT id, title FROM series;")
        existing_series = cursor.fetchall()
        
        # Criar dicionário de títulos normalizados para IDs
        existing_titles_map = {}
        for serie_id, title in existing_series:
            titulo_norm = normalizar_titulo(title)
            existing_titles_map[titulo_norm] = {
                'id': serie_id,
                'titulo_original': title
            }
        
        print(f"   📚 {len(existing_series)} HQs já existem no banco")
        
    except Exception as e:
        print(f"❌ Erro ao buscar séries existentes: {e}")
        conn.close()
        sys.exit(1)
    
    # Processar cada linha da planilha
    print("\n" + "=" * 80)
    print("🔄 PROCESSANDO PLANILHA")
    print("=" * 80)
    
    stats = {
        'adicionadas': 0,
        'atualizadas': 0,
        'ignoradas': 0,
        'erros': 0
    }
    
    for idx, row in df.iterrows():
        try:
            # Ler dados da linha
            nome = str(row.get('NOME', '')).strip()
            
            # Ignorar linhas vazias
            if not nome or nome == 'nan' or nome == '':
                stats['ignoradas'] += 1
                continue
            
            titulo_norm = normalizar_titulo(nome)
            
            # Preparar dados
            autor = None if pd.isna(row.get('AUTOR')) else str(row['AUTOR']).strip()
            editora = None if pd.isna(row.get('EDITORA')) else str(row['EDITORA']).strip()
            
            # Números - validar e ajustar para manter integridade
            lendo_raw = row.get('Nº ISSUE LENDO', 0)
            baixado_raw = row.get('Nº BAIXADO', lendo_raw)
            total_raw = row.get('TOTAL ISSUES', baixado_raw)
            
            lendo, baixado, total = validar_e_ajustar_numeros(lendo_raw, baixado_raw, total_raw)
            
            # Tipo de série (mapeamento inteligente)
            tipo_excel = row.get('TIPO', 'Em andamento')
            tipo = mapear_tipo_serie(tipo_excel)
            
            # Finalizada (conversão para boolean)
            finalizada_excel = row.get('FINALIZADA', 'Não')
            is_completed = mapear_finalizada(finalizada_excel)
            
            # Capa e notas
            capa = None if pd.isna(row.get('CAPA')) else str(row['CAPA']).strip()
            notas = None if pd.isna(row.get('NOTAS')) else str(row['NOTAS']).strip()
            
            # Verificar se HQ já existe no banco
            if titulo_norm in existing_titles_map:
                # ATUALIZAR HQ EXISTENTE
                serie_id = existing_titles_map[titulo_norm]['id']
                
                cursor.execute("""
                    UPDATE series SET
                        title = %s,
                        author = %s,
                        publisher = %s,
                        read_issues = %s,
                        downloaded_issues = %s,
                        total_issues = %s,
                        is_completed = %s,
                        series_type = %s,
                        cover_url = %s,
                        notes = %s,
                        date_updated = %s
                    WHERE id = %s
                """, (
                    nome, autor, editora,
                    lendo, baixado, total,
                    is_completed, tipo,
                    capa, notas,
                    datetime.now().isoformat(),
                    serie_id
                ))
                
                stats['atualizadas'] += 1
                print(f"  ✏️  ATUALIZADA: {nome} (ID: {serie_id})")
                
            else:
                # ADICIONAR NOVA HQ
                cursor.execute("""
                    INSERT INTO series (
                        title, author, publisher,
                        read_issues, downloaded_issues, total_issues,
                        is_completed, series_type,
                        cover_url, notes,
                        date_added
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    nome, autor, editora,
                    lendo, baixado, total,
                    is_completed, tipo,
                    capa, notas,
                    datetime.now().isoformat()
                ))
                
                new_id = cursor.fetchone()[0]
                stats['adicionadas'] += 1
                print(f"  ✅ NOVA: {nome} (ID: {new_id})")
                
                # Adicionar ao mapa para evitar duplicação no mesmo import
                existing_titles_map[titulo_norm] = {
                    'id': new_id,
                    'titulo_original': nome
                }
            
            # Commit a cada X registros (configurável)
            if (stats['adicionadas'] + stats['atualizadas']) % COMMIT_BATCH_SIZE == 0:
                conn.commit()
                
        except Exception as e:
            stats['erros'] += 1
            print(f"  ❌ ERRO na linha {idx + 2} ({nome}): {e}")
    
    # Commit final
    try:
        conn.commit()
        print(f"\n✅ Commit final realizado!")
    except Exception as e:
        print(f"\n❌ Erro ao fazer commit final: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    # Verificar resultado final
    cursor.execute("SELECT COUNT(*) FROM series;")
    total_final = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    # Relatório final
    print("\n" + "=" * 80)
    print("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   ➕ Adicionadas:  {stats['adicionadas']}")
    print(f"   ✏️  Atualizadas:  {stats['atualizadas']}")
    print(f"   ⏭️  Ignoradas:    {stats['ignoradas']}")
    print(f"   ❌ Erros:        {stats['erros']}")
    print(f"   📚 Total no banco: {total_final}")
    
    print("\n" + "=" * 80)
    print("🌐 Acesse sua estante em: https://estantedoleitor.up.railway.app")
    print("=" * 80)
    
    if stats['erros'] > 0:
        print(f"\n⚠️  Atenção: {stats['erros']} erros ocorreram durante a importação.")
        print("   Revise as mensagens acima para mais detalhes.")

if __name__ == "__main__":
    try:
        importar_planilha()
    except KeyboardInterrupt:
        print("\n\n❌ Importação cancelada pelo usuário (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
