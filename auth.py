import bcrypt
from database import obter_conexao


def cadastrar_usuario(nome, email, senha, tipo_usuario):
    conn = obter_conexao()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Verifica se o email já está cadastrado
        cursor.execute("SELECT id_usuario FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            print(f"Já existe um usuário cadastrado com o email {email}.")
            return None

        # Gera o hash da senha — você só passa a senha normal, ele cuida do resto
        senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo_usuario)
            VALUES (%s, %s, %s, %s)
            RETURNING id_usuario;
            """,
            (nome, email, senha_hash, tipo_usuario),
        )

        id_usuario = cursor.fetchone()[0]
        conn.commit()
        print(f"Usuário '{nome}' cadastrado com sucesso! ID: {id_usuario}")
        return id_usuario

    except Exception as e:
        conn.rollback()
        print(f"Erro ao cadastrar usuário: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def fazer_login(email, senha):
    conn = obter_conexao()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id_usuario, nome, senha_hash, tipo_usuario, ativo
            FROM usuarios
            WHERE email = %s
            """,
            (email,),
        )

        resultado = cursor.fetchone()

        # Email não encontrado
        if not resultado:
            print("Email ou senha incorretos.")
            return None

        id_usuario, nome, senha_hash, tipo_usuario, ativo = resultado

        # Usuário desativado
        if not ativo:
            print("Usuário inativo. Entre em contato com o administrador.")
            return None

        # Compara a senha digitada com o hash salvo no banco
        senha_correta = bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
        if not senha_correta:
            print("Email ou senha incorretos.")
            return None

        # Retorna os dados do usuário logado como dicionário
        print(f"Login realizado com sucesso! Bem-vindo, {nome}.")
        return {
            "id_usuario":  id_usuario,
            "nome":        nome,
            "tipo_usuario": tipo_usuario,
        }

    except Exception as e:
        print(f"Erro ao fazer login: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def alterar_senha(id_usuario, senha_atual, nova_senha):
    conn = obter_conexao()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT senha_hash FROM usuarios WHERE id_usuario = %s",
            (id_usuario,),
        )
        resultado = cursor.fetchone()
        if not resultado:
            print("Usuário não encontrado.")
            return False

        # Verifica se a senha atual está correta antes de trocar
        if not bcrypt.checkpw(senha_atual.encode("utf-8"), resultado[0].encode("utf-8")):
            print("Senha atual incorreta.")
            return False

        nova_hash = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            "UPDATE usuarios SET senha_hash = %s WHERE id_usuario = %s",
            (nova_hash, id_usuario),
        )

        conn.commit()
        print("Senha alterada com sucesso!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Erro ao alterar senha: {e}")
        return False

    finally:
        cursor.close()
        conn.close()
