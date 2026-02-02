#!/usr/bin/env python3
"""
IMPORTAÇÃO INTELIGENTE: Excel → PostgreSQL Railway
Atualiza HQs existentes e adiciona novas, sem duplicar
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
            escolha = input(f"\n👉 Digite o número do arquivo que deseja importar [1-{len(arquivos_excel)}]: ").strip()
            
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

def importar_excel_inteligente(EXCEL_FILE):
    print("\n" + "=" * 70)
    print("🔄 IMPORTAÇÃO INTELIGENTE: EXCEL → RAILWAY")
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
    
    # Buscar HQs existentes (pelo ID se existir, senão pelo NOME)
    print("\n📚 Verificando HQs existentes no banco...")
    cursor.execute("SELECT id, title FROM series;")
    rows = cursor.fetchall()
    
    existing_series = {row[0]: row[1] for row in rows}
    existing_titles = {row[1].lower().strip(): row[0] for row in rows}
    
    print(f"   {len(existing_series)} HQs já existem no banco")
    
    # Processar
    print("\n🔄 Processando planilha...")
    print("-" * 70)
    
    adicionadas = 0
    atualizadas = 0
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
            
            # Números
            lendo = int(row.get('Nº ISSUE LENDO', 0)) if pd.notna(row.get('Nº ISSUE LENDO')) else 0
            baixado = int(row.get('Nº BAIXADO', lendo)) if pd.notna(row.get('Nº BAIXADO')) else lendo
            total = int(row.get('TOTAL ISSUES', baixado)) if pd.notna(row.get('TOTAL ISSUES')) else baixado
            
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
            
            # Verificar se já existe (por ID ou por título)
            existe_no_banco = False
            id_no_banco = None
            
            if serie_id and serie_id in existing_series:
                # Existe pelo ID
                existe_no_banco = True
                id_no_banco = serie_id
            elif nome.lower().strip() in existing_titles:
                # Existe pelo título
                existe_no_banco = True
                id_no_banco = existing_titles[nome.lower().strip()]
            
            if existe_no_banco:
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
                print(f"  ✏️ Atualizada: {nome} (ID: {id_no_banco})")
            else:
                # ADICIONAR NOVA
                cursor.execute("""
                    INSERT INTO series (
                        title, author, publisher, 
                        read_issues, downloaded_issues, total_issues,
                        is_completed, series_type,
                        cover_url, notes, date_added
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    nome, autor, editora,
                    lendo, baixado, total,
                    is_completed, tipo,
                    capa, notas, datetime.now().isoformat()
                ))
                adicionadas += 1
                print(f"  ✅ Nova: {nome}")
            
            # Commit a cada 10 registros para evitar perder tudo em caso de erro
            if (adicionadas + atualizadas) % 10 == 0:
                conn.commit()
                
        except Exception as e:
            erros += 1
            print(f"  ❌ Erro na linha {idx + 1} ({nome}): {e}")
    
    # Commit final
    try:
        conn.commit()
        print(f"\n✅ Commit final realizado!")
    except Exception as e:
        print(f"\n❌ Erro ao fazer commit: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    
    # Verificar resultado
    cursor.execute("SELECT COUNT(*) FROM series;")
    total_final = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("🎉 IMPORTAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"\n📊 Resultado:")
    print(f"   ➕ Adicionadas: {adicionadas}")
    print(f"   ✏️ Atualizadas: {atualizadas}")
    print(f"   ⏭️ Ignoradas: {ignoradas}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📚 Total no banco: {total_final}")
    print(f"\n🌐 Acesse: https://estantedoleitor.up.railway.app")
    print("=" * 70)

if __name__ == "__main__":
    try:
        # Selecionar arquivo
        arquivo_escolhido = selecionar_arquivo_excel()
        
        # Importar
        importar_excel_inteligente(arquivo_escolhido)
    except KeyboardInterrupt:
        print("\n\n❌ Importação cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
