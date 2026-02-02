#!/usr/bin/env python3
"""
SINCRONIZAÇÃO FORÇADA: Excel → PostgreSQL Railway
Sobrescreve os dados do banco com os valores da planilha Excel
Use quando precisar RESTAURAR dados da planilha para o banco
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
    
    # Buscar todos os arquivos Excel na pasta atual
    arquivos_excel = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    if not arquivos_excel:
        print("\n❌ Nenhum arquivo Excel (.xlsx ou .xls) encontrado na pasta atual!")
        print("\n💡 Dica: Coloque sua planilha na mesma pasta deste script.")
        sys.exit(1)
    
    # Ordenar por data de modificação (mais recente primeiro)
    arquivos_excel.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print(f"\n📚 {len(arquivos_excel)} arquivo(s) Excel encontrado(s):\n")
    
    # Listar arquivos com informações
    for i, arquivo in enumerate(arquivos_excel, 1):
        tamanho = os.path.getsize(arquivo)
        tamanho_kb = tamanho / 1024
        data_mod = datetime.fromtimestamp(os.path.getmtime(arquivo))
        data_str = data_mod.strftime('%d/%m/%Y %H:%M')
        
        print(f"  [{i}] {arquivo}")
        print(f"      📅 Modificado: {data_str} | 📊 Tamanho: {tamanho_kb:.1f} KB")
        print()
    
    # Solicitar escolha do usuário
    while True:
        try:
            print("=" * 70)
            escolha = input(f"\n👉 Digite o número do arquivo para RESTAURAR os dados [1-{len(arquivos_excel)}]: ").strip()
            
            if not escolha:
                print("❌ Você precisa digitar um número!")
                continue
            
            numero = int(escolha)
            
            if 1 <= numero <= len(arquivos_excel):
                arquivo_selecionado = arquivos_excel[numero - 1]
                print(f"\n✅ Arquivo selecionado: {arquivo_selecionado}")
                return arquivo_selecionado
            else:
                print(f"❌ Número inválido! Digite um número entre 1 e {len(arquivos_excel)}")
        except ValueError:
            print("❌ Digite apenas números!")
        except KeyboardInterrupt:
            print("\n\n❌ Operação cancelada pelo usuário")
            sys.exit(0)

def sincronizar_do_excel(EXCEL_FILE):
    print("\n" + "=" * 70)
    print("🔄 SINCRONIZAÇÃO FORÇADA: EXCEL → RAILWAY")
    print("⚠️  OS VALORES DO BANCO SERÃO SOBRESCRITOS COM OS DA PLANILHA!")
    print("=" * 70)
    
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
    
    # Buscar HQs existentes no banco
    print("\n📚 Verificando HQs existentes no banco...")
    cursor.execute("SELECT id, title FROM series;")
    rows = cursor.fetchall()
    
    existing_by_id = {row[0]: row[1] for row in rows}
    existing_by_title = {row[1].lower().strip(): row[0] for row in rows}
    
    print(f"   {len(existing_by_id)} HQs encontradas no banco")
    
    # Processar
    print("\n🔄 Sincronizando dados da planilha...")
    print("-" * 70)
    
    atualizadas = 0
    nao_encontradas = 0
    ignoradas = 0
    erros = 0
    
    for idx, row in df.iterrows():
        try:
            # Ler dados da linha
            nome = str(row.get('NOME', '')).strip()
            if not nome or nome == 'nan':
                ignoradas += 1
                continue
            
            # Verificar se tem ID na planilha
            serie_id = row.get('ID', None)
            if pd.notna(serie_id):
                serie_id = int(serie_id)
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
            
            # Números - ATENÇÃO: pegando direto da planilha
            lendo = int(row.get('Nº ISSUE LENDO', 0)) if pd.notna(row.get('Nº ISSUE LENDO')) else 0
            baixado = int(row.get('Nº BAIXADO', 0)) if pd.notna(row.get('Nº BAIXADO')) else 0
            total = int(row.get('TOTAL ISSUES', 0)) if pd.notna(row.get('TOTAL ISSUES')) else 0
            
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
            
            # Verificar se existe no banco (por ID ou por título)
            id_no_banco = None
            
            if serie_id and serie_id in existing_by_id:
                # Existe pelo ID
                id_no_banco = serie_id
            elif nome.lower().strip() in existing_by_title:
                # Existe pelo título
                id_no_banco = existing_by_title[nome.lower().strip()]
            
            if id_no_banco:
                # ATUALIZAR com os valores da planilha (SOBRESCREVER)
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
                print(f"  ✅ Atualizada: {nome} (Lendo:{lendo}, Baixadas:{baixado}, Total:{total})")
            else:
                # Não encontrada no banco
                nao_encontradas += 1
                print(f"  ⚠️  Não encontrada no banco: {nome} (será ignorada)")
            
            # Commit a cada 10 registros
            if (atualizadas) % 10 == 0 and atualizadas > 0:
                conn.commit()
                
        except Exception as e:
            erros += 1
            print(f"  ❌ Erro na linha {idx + 1} ({nome}): {e}")
    
    # Commit final
    try:
        conn.commit()
        print(f"\n✅ Alterações salvas no banco!")
    except Exception as e:
        print(f"\n❌ Erro ao salvar: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   ✅ Atualizadas: {atualizadas}")
    print(f"   ⚠️  Não encontradas: {nao_encontradas}")
    print(f"   ⏭️  Ignoradas (linhas vazias): {ignoradas}")
    print(f"   ❌ Erros: {erros}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("\n💡 Os números foram restaurados da planilha!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        print("\n" + "=" * 70)
        print("⚠️  ATENÇÃO - SINCRONIZAÇÃO FORÇADA")
        print("=" * 70)
        print("\nEste script vai SOBRESCREVER os dados do banco com os da planilha.")
        print("Use quando você tiver uma planilha CORRETA e quiser restaurar os dados.")
        print("\n💡 Campos que serão restaurados:")
        print("   - Nº ISSUE LENDO")
        print("   - Nº BAIXADO")
        print("   - TOTAL ISSUES")
        print("   - E todos os outros campos da HQ")
        print("\n⚠️  As EDIÇÕES cadastradas NÃO serão afetadas (tabela issues).")
        print("=" * 70)
        
        confirmacao = input("\nDeseja continuar? (s/n): ").strip().lower()
        
        if confirmacao not in ['s', 'sim', 'y', 'yes']:
            print("\n❌ Operação cancelada pelo usuário")
            sys.exit(0)
        
        # Selecionar arquivo
        arquivo_escolhido = selecionar_arquivo_excel()
        
        # Confirmação final
        print(f"\n⚠️  Você vai restaurar dados de: {arquivo_escolhido}")
        print("   Os valores do BANCO serão SOBRESCRITOS com os da PLANILHA.")
        
        confirmacao_final = input("\nTem certeza? (s/n): ").strip().lower()
        
        if confirmacao_final not in ['s', 'sim', 'y', 'yes']:
            print("\n❌ Operação cancelada")
            sys.exit(0)
        
        # Sincronizar
        sincronizar_do_excel(arquivo_escolhido)
        
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
