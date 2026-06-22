import os
import psycopg2
from dotenv import load_dotenv

# Carreda o arquivo .env
load_dotenv()


def obter_conexao():
    url_banco = os.getenv("DATABASE_URL")

    # Se a variável vier vazia, o .env não foi lido!
    if not url_banco:
        print(
            "ERRO CRÍTICO: A variável DATABASE_URL não foi encontrada no arquivo .env!"
        )
        print("Verifique se o arquivo .env existe e está na raiz do projeto.")
        return None

    try:
        # Tenta conectar usando a URL da nuvem
        return psycopg2.connect(url_banco)
    except Exception as e:
        print(f"Erro ao conectar ao Neon.tech: {e}")
        return None


if __name__ == "__main__":
    print("Testando conexão...")
    conn = obter_conexao()
    if conn:
        print("Conexão com o Neon.tech realizada com sucesso!")
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS test (id integer PRIMARY KEY, texto text)"""
        )
        cursor.execute(
            """
                       INSERT INTO test (id, texto)
                    VALUES (%s, %s);
        """,
            (1, "Ariel"),
        )
        conn.commit()
        conn.close()
