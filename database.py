import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def obter_conexao():
    url_banco = os.getenv("DATABASE_URL")

    if not url_banco:
        print("ERRO CRÍTICO: A variável DATABASE_URL não foi encontrada no arquivo .env!")
        print("Verifique se o arquivo .env existe e está na raiz do projeto.")
        return None

    try:
        conn = psycopg2.connect(url_banco)
        conn.autocommit = False  # garante que todo commit seja explícito (mais seguro)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None


if __name__ == "__main__":
    print("Testando conexão...")
    conn = obter_conexao()
    if conn:
        print("Conexão com o Neon.tech realizada com sucesso!")
        conn.close()
    else:
        print("Falha na conexão. Verifique o arquivo .env.")
