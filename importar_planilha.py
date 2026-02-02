"""
Script de Importação Interativo
Permite escolher qual planilha importar
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os
import glob

def list_excel_files():
    """Lista todos os arquivos Excel no diretório"""
    excel_files = glob.glob('*.xlsx')
    if not excel_files:
        print("\n❌ Nenhum arquivo Excel (.xlsx) encontrado no diretório atual")
        return None
    
    print("\n📁 Arquivos Excel disponíveis:")
    for i, file in enumerate(excel_files, 1):
        size = os.path.getsize(file) / 1024  # KB
        print(f"   {i}. {file} ({size:.1f} KB)")
    
    return excel_files

def init_database(db_path='hq_manager.db'):
    """Inicializa o banco de dados"""
    print(f"\n🔧 Inicializando banco: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Criar tabela series
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            author TEXT,
            publisher TEXT,
            total_issues INTEGER DEFAULT 0,
            downloaded_issues INTEGER DEFAULT 0,
            read_issues INTEGER DEFAULT 0,
            cover_url TEXT,
            notes TEXT,
            date_added TEXT NOT NULL,
            date_updated TEXT,
            is_completed BOOLEAN DEFAULT 0,
            series_type TEXT DEFAULT 'em_andamento'
        )
    ''')
    
    # Adicionar colunas se não existirem
    try:
        cursor.execute("ALTER TABLE series ADD COLUMN is_completed BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE series ADD COLUMN series_type TEXT DEFAULT 'em_andamento'")
    except sqlite3.OperationalError:
        pass
    
    # Criar tabela issues
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            issue_number INTEGER NOT NULL,
            title TEXT,
            is_read BOOLEAN DEFAULT 0,
            is_downloaded BOOLEAN DEFAULT 1,
            date_added TEXT NOT NULL,
            date_read TEXT,
            FOREIGN KEY (series_id) REFERENCES series (id) ON DELETE CASCADE,
            UNIQUE(series_id, issue_number)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Banco inicializado!")

def determine_series_type(row):
    """Determina o tipo da série"""
    if 'TIPO' in row.index and pd.notna(row['TIPO']):
        tipo = str(row['TIPO']).lower().strip()
        tipo_map = {
            'finalizada': 'finalizada',
            'em andamento': 'em_andamento',
            'lançamento': 'lancamento',
            'edição especial': 'edicao_especial',
            'especial': 'edicao_especial'
        }
        return tipo_map.get(tipo, 'em_andamento')
    return 'em_andamento'

def import_excel(excel_file, db_path='hq_manager.db'):
    """Importa dados do Excel"""
    
    print(f"\n📖 Lendo planilha: {excel_file}")
    df = pd.read_excel(excel_file)
    
    print(f"✓ {len(df)} HQs encontradas")
    print(f"📋 Colunas: {df.columns.tolist()}")
    
    # Conectar ao banco
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    imported = 0
    updated = 0
    errors = 0
    
    print("\n⚙️  Importando...")
    
    for idx, row in df.iterrows():
        try:
            # Dados básicos
            nome = str(row['NOME']).strip()
            
            autor = None
            if 'AUTOR' in df.columns and pd.notna(row['AUTOR']):
                autor = str(row['AUTOR']).strip()
            
            editora = None
            if 'EDITORA' in df.columns and pd.notna(row['EDITORA']) and str(row['EDITORA']).strip() != '-':
                editora = str(row['EDITORA']).strip()
            
            read_issues = 0
            if 'Nº ISSUE LENDO' in df.columns and pd.notna(row['Nº ISSUE LENDO']):
                read_issues = int(row['Nº ISSUE LENDO'])
            
            downloaded_issues = 0
            if 'Nº BAIXADO' in df.columns and pd.notna(row['Nº BAIXADO']):
                downloaded_issues = int(row['Nº BAIXADO'])
            
            total_issues = downloaded_issues
            if 'TOTAL ISSUES' in df.columns and pd.notna(row['TOTAL ISSUES']):
                total_issues = int(row['TOTAL ISSUES'])
            
            is_completed = False
            if 'FINALIZADA' in df.columns and pd.notna(row['FINALIZADA']):
                finalizada_str = str(row['FINALIZADA']).lower().strip()
                is_completed = finalizada_str in ['sim', 'yes', '1', 'true']
            
            notas = None
            if 'NOTAS' in df.columns and pd.notna(row['NOTAS']):
                notas = str(row['NOTAS']).strip()
            
            cover_url = None
            if 'CAPA' in df.columns and pd.notna(row['CAPA']):
                cover_url = str(row['CAPA']).strip()
            
            series_type = determine_series_type(row)
            
            # Verificar se existe
            cursor.execute("SELECT id, cover_url FROM series WHERE title = ?", (nome,))
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar
                series_id = existing[0]
                existing_cover = existing[1]
                
                if not cover_url and existing_cover:
                    cover_url = existing_cover
                
                cursor.execute('''
                    UPDATE series 
                    SET author = ?, publisher = ?, total_issues = ?, downloaded_issues = ?, 
                        read_issues = ?, is_completed = ?, series_type = ?, cover_url = ?, 
                        notes = ?, date_updated = ?
                    WHERE id = ?
                ''', (autor, editora, total_issues, downloaded_issues, read_issues,
                      is_completed, series_type, cover_url, notas, 
                      datetime.now().isoformat(), series_id))
                
                print(f"  ↻ {nome} - ATUALIZADA")
                updated += 1
            else:
                # Inserir nova
                cursor.execute('''
                    INSERT INTO series 
                    (title, author, publisher, total_issues, downloaded_issues, read_issues, 
                     is_completed, series_type, cover_url, notes, date_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, autor, editora, total_issues, downloaded_issues, read_issues,
                      is_completed, series_type, cover_url, notas, datetime.now().isoformat()))
                
                series_id = cursor.lastrowid
                
                # Criar issues
                date_now = datetime.now().isoformat()
                for issue_num in range(1, downloaded_issues + 1):
                    is_read = 1 if issue_num <= read_issues else 0
                    date_read = date_now if is_read else None
                    
                    try:
                        cursor.execute('''
                            INSERT INTO issues
                            (series_id, issue_number, is_read, is_downloaded, date_added, date_read)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (series_id, issue_num, is_read, 1, date_now, date_read))
                    except sqlite3.IntegrityError:
                        pass
                
                print(f"  ✓ {nome} - NOVA")
                imported += 1
                
        except Exception as e:
            print(f"  ✗ Erro linha {idx + 1}: {e}")
            errors += 1
    
    conn.commit()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 70)
    print("✅ IMPORTAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print(f"✓ Novas: {imported}")
    print(f"↻ Atualizadas: {updated}")
    if errors > 0:
        print(f"✗ Erros: {errors}")
    
    # Estatísticas
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM series")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT series_type, COUNT(*) FROM series GROUP BY series_type")
    stats = cursor.fetchall()
    
    print(f"\n📊 Total no banco: {total} séries")
    print(f"\n📊 Por tipo:")
    for tipo, count in stats:
        tipo_nome = {
            'em_andamento': 'Em Andamento',
            'finalizada': 'Finalizada',
            'lancamento': 'Lançamento',
            'edicao_especial': 'Edição Especial'
        }.get(tipo, tipo)
        print(f"   {tipo_nome}: {count}")
    
    conn.close()

def main():
    print("=" * 70)
    print("IMPORTAÇÃO INTERATIVA DE PLANILHA")
    print("=" * 70)
    
    # Listar arquivos
    excel_files = list_excel_files()
    if not excel_files:
        return
    
    # Escolher arquivo
    while True:
        try:
            choice = input(f"\n📝 Escolha o arquivo (1-{len(excel_files)}) ou 'q' para sair: ").strip()
            
            if choice.lower() == 'q':
                print("👋 Saindo...")
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(excel_files):
                selected_file = excel_files[idx]
                break
            else:
                print(f"❌ Opção inválida! Escolha entre 1 e {len(excel_files)}")
        except ValueError:
            print("❌ Digite um número válido ou 'q' para sair")
    
    print(f"\n✓ Arquivo selecionado: {selected_file}")
    
    # Perguntar nome do banco
    db_default = 'hq_manager.db'
    db_path = input(f"\n💾 Nome do banco de dados [Enter = {db_default}]: ").strip()
    if not db_path:
        db_path = db_default
    
    # Confirmar
    print(f"\n⚠️  Prestes a importar:")
    print(f"   📄 Planilha: {selected_file}")
    print(f"   💾 Banco: {db_path}")
    confirm = input(f"\n❓ Continuar? (s/n): ").strip().lower()
    
    if confirm != 's':
        print("❌ Operação cancelada")
        return
    
    # Importar
    init_database(db_path)
    import_excel(selected_file, db_path)
    
    print("\n💡 Próximos passos:")
    print("   1. python main.py")
    print("   2. Abra index.html no navegador")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
