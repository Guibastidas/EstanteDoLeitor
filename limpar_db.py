import os
import psycopg2
from dotenv import load_dotenv

# carrega as variaveis de um arquivo .env se existir localmente
load_dotenv()

def limpar_tabela():
    connection = None
    try:
        # o railway fornece a database_url que simplifica a conexao
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            # alternativa caso voce prefira usar as variaveis separadas
            connection = psycopg2.connect(
                host=os.getenv("PGHOST"),
                database=os.getenv("PGDATABASE"),
                user=os.getenv("PGUSER"),
                password=os.getenv("PGPASSWORD"),
                port=os.getenv("PGPORT")
            )
        else:
            connection = psycopg2.connect(database_url)

        cursor = connection.cursor()
        
        # substitua nome_da_tabela pelo nome real
        sql = "truncate table nome_da_tabela restart identity cascade;"
        
        cursor.execute(sql)
        connection.commit()
        print("tabela limpa e indices reiniciados com sucesso.")

    except Exception as error:
        print(f"falha ao executar operacao: {error}")
    
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    limpar_tabela()