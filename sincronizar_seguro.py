#!/usr/bin/env python3
"""
SINCRONIZAÇÃO SEGURA: Excel → PostgreSQL Railway
Versão melhorada com validação e prévia dos dados
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os

# Configuração
DATABASE_URL = "postgresql://postgres:PlNkuSjIiUdRzIoutUpzDbwlgSrWKwcW@crossover.proxy.rlwy.net:15604/railway"

def selecionar_arquivo_excel():
    """Permite ao usuário selecionar qual arquivo Excel importar"""
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
            escolha = input(f"\n👉 Digite o número do arquivo para RESTAURAR [1-{len(arquivos_excel)}]: ").strip()
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

def validar_e_mostrar_previa(df):
    """Valida e mostra prévia dos dados"""
    print("\n" + "=" * 70)
    print("🔍 VALIDAÇÃO E PRÉVIA DOS DADOS")
    print("=" * 70)
    
    # Verificar colunas necessárias
    colunas_necessarias = ['NOME', 'Nº ISSUE LENDO', 'Nº BAIXADO', 'TOTAL ISSUES']
    colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
    
    if colunas_faltando:
        print(f"\n❌ ERRO: Colunas faltando na planilha:")
        for col in colunas_faltando:
            print(f"   - {col}")
        print(f"\n📋 Colunas encontradas: {list(df.columns)}")
        return False
    
    # Contar campos vazios
    print("\n📊 Análise da planilha:")
    print(f"   Total de linhas: {len(df)}")
    
    vazios_lendo = df['Nº ISSUE LENDO'].isna().sum()
    vazios_baixado = df['Nº BAIXADO'].isna().sum()
    vazios_total = df['TOTAL ISSUES'].isna().sum()
    
    print(f"\n⚠️  Campos VAZIOS que serão importados como 0:")
    print(f"   Nº ISSUE LENDO: {vazios_lendo} campos vazios")
    print(f"   Nº BAIXADO: {vazios_baixado} campos vazios")
    print(f"   TOTAL ISSUES: {vazios_total} campos vazios")
    
    if vazios_lendo > 0 or vazios_baixado > 0:
        print(f"\n⚠️  ATENÇÃO CRÍTICA!")
        print(f"   Existem {vazios_lendo} HQs com 'Nº ISSUE LENDO' vazio")
        print(f"   Existem {vazios_baixado} HQs com 'Nº BAIXADO' vazio")
        print(f"\n   Se continuar, estes campos serão ZERADOS no banco!")
        print(f"\n💡 Recomendação: Cancele e preencha os campos vazios antes.")
    
    # Mostrar prévia das primeiras 10 HQs
    print("\n" + "=" * 100)
    print("📋 PRÉVIA - Primeiras 10 HQs que serão importadas:")
    print("=" * 100)
    print(f"\n{'NOME':<35} | {'LENDO':<8} | {'BAIXADAS':<10} | {'TOTAL':<8}")
    print("-" * 100)
    
    for idx, row in df.head(10).iterrows():
        nome = str(row.get('NOME', '')).strip()
        if not nome or nome == 'nan':
            continue
        
        lendo = row.get('Nº ISSUE LENDO', 0)
        baixado = row.get('Nº BAIXADO', 0)
        total = row.get('TOTAL ISSUES', 0)
        
        # Converter para int
        try:
            lendo = int(lendo) if pd.notna(lendo) else 0
            baixado = int(baixado) if pd.notna(baixado) else 0
            total = int(total) if pd.notna(total) else 0
        except:
            lendo = 0
            baixado = 0
            total = 0
        
        # Truncar nome se muito grande
        nome_display = nome[:33] + "..." if len(nome) > 35 else nome
        
        # Marcar com ⚠️ se algum campo for 0
        alerta = "⚠️" if (lendo == 0 or baixado == 0) and total > 0 else ""
        
        print(f"{nome_display:<35} | {lendo:<8} | {baixado:<10} | {total:<8} {alerta}")
    
    if len(df) > 10:
        print(f"\n... e mais {len(df) - 10} HQs")
    
    return True

def sincronizar_segura(EXCEL_FILE):
    print("\n" + "=" * 70)
    print("🔄 SINCRONIZAÇÃO SEGURA: EXCEL → RAILWAY")
    print("=" * 70)
    
    print(f"\n📖 Lendo planilha: {EXCEL_FILE}")
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ {len(df)} linhas encontradas")
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        sys.exit(1)
    
    # Validar e mostrar prévia
    if not validar_e_mostrar_previa(df):
        print("\n❌ Validação falhou. Corrija a planilha e tente novamente.")
        sys.exit(1)
    
    # Confirmação
    print("\n" + "=" * 70)
    confirmacao = input("\n⚠️  Deseja continuar com a importação? (s/n): ").strip().lower()
    
    if confirmacao not in ['s', 'sim', 'y', 'yes']:
        print("\n❌ Operação cancelada")
        sys.exit(0)
    
    # Conectar ao banco
    print("\n🔌 Conectando ao Railway...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Buscar HQs existentes
    print("\n📚 Buscando HQs no banco...")
    cursor.execute("SELECT id, title FROM series;")
    rows = cursor.fetchall()
    
    existing_by_id = {row[0]: row[1] for row in rows}
    existing_by_title = {row[1].lower().strip(): row[0] for row in rows}
    
    print(f"   {len(existing_by_id)} HQs encontradas no banco")
    
    # Processar
    print("\n🔄 Sincronizando dados...")
    print("-" * 70)
    
    atualizadas = 0
    nao_encontradas = 0
    ignoradas = 0
    erros = 0
    
    for idx, row in df.iterrows():
        try:
            # Ler dados
            nome = str(row.get('NOME', '')).strip()
            if not nome or nome == 'nan':
                ignoradas += 1
                continue
            
            # ID
            serie_id = row.get('ID', None)
            if pd.notna(serie_id):
                try:
                    serie_id = int(serie_id)
                except:
                    serie_id = None
            else:
                serie_id = None
            
            # Preparar dados
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
            
            # Números - COM VALIDAÇÃO EXTRA
            lendo_raw = row.get('Nº ISSUE LENDO', None)
            baixado_raw = row.get('Nº BAIXADO', None)
            total_raw = row.get('TOTAL ISSUES', None)
            
            # Converter com cuidado
            try:
                lendo = int(lendo_raw) if pd.notna(lendo_raw) and str(lendo_raw).strip() != '' else 0
            except:
                lendo = 0
            
            try:
                baixado = int(baixado_raw) if pd.notna(baixado_raw) and str(baixado_raw).strip() != '' else 0
            except:
                baixado = 0
            
            try:
                total = int(total_raw) if pd.notna(total_raw) and str(total_raw).strip() != '' else 0
            except:
                total = 0
            
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
            
            # Verificar se existe no banco
            id_no_banco = None
            
            if serie_id and serie_id in existing_by_id:
                id_no_banco = serie_id
            elif nome.lower().strip() in existing_by_title:
                id_no_banco = existing_by_title[nome.lower().strip()]
            
            if id_no_banco:
                # ATUALIZAR
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
                    id_no_banco
                ))
                atualizadas += 1
                
                # Mostrar só se tiver valores válidos ou se for múltiplo de 10
                if atualizadas % 10 == 0 or lendo > 0 or baixado > 0:
                    print(f"  ✅ {nome[:40]:<40} | L:{lendo:>3} B:{baixado:>3} T:{total:>3}")
            else:
                nao_encontradas += 1
                if nao_encontradas <= 5:  # Mostrar só as primeiras 5
                    print(f"  ⚠️  Não encontrada: {nome}")
            
            # Commit a cada 10
            if atualizadas % 10 == 0 and atualizadas > 0:
                conn.commit()
                
        except Exception as e:
            erros += 1
            print(f"  ❌ Erro em '{nome}': {e}")
    
    # Commit final
    try:
        conn.commit()
        print(f"\n✅ Alterações salvas no banco!")
    except Exception as e:
        print(f"\n❌ Erro ao salvar: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   ✅ Atualizadas: {atualizadas}")
    print(f"   ⚠️  Não encontradas: {nao_encontradas}")
    print(f"   ⏭️  Ignoradas: {ignoradas}")
    print(f"   ❌ Erros: {erros}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("=" * 70)

if __name__ == "__main__":
    try:
        print("\n" + "=" * 70)
        print("⚠️  SINCRONIZAÇÃO SEGURA COM VALIDAÇÃO")
        print("=" * 70)
        print("\nEste script vai:")
        print("  1. Validar os dados da planilha")
        print("  2. Mostrar uma prévia do que será importado")
        print("  3. Pedir confirmação antes de executar")
        print("  4. Sobrescrever os dados do banco com a planilha")
        print("=" * 70)
        
        arquivo = selecionar_arquivo_excel()
        sincronizar_segura(arquivo)
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
