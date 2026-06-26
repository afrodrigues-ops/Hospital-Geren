from database import obter_conexao

class Paciente:
    def __init__(self, nome, cpf, idade, urgencia):
        self.nome = nome
        self.cpf = cpf
        self.idade = idade
        self.urgencia = urgencia

    def mostrar_no(self):
        # Mapeia o número da urgência de volta para texto para ficar bonito na tela
        niveis = {4: "Emergência", 3: "Muito Urgente", 2: "Urgente", 1: "Pouco Urgente", 0: "Não Urgente"}
        txt_urgencia = niveis.get(self.urgencia, "Desconhecido")
        
        print(f"Paciente: {self.nome} | CPF: {self.cpf} | Idade: {self.idade} | Urgência: {txt_urgencia}")

def cadastrar_paciente(nome, cpf, data_nascimento, sexo=None, telefone=None, endereco=None):
    conn = obter_conexao()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Verifica se já existe um paciente com esse CPF
        cursor.execute("SELECT id_paciente FROM pacientes WHERE cpf = %s", (cpf,))
        if cursor.fetchone():
            print(f"Já existe um paciente cadastrado com o CPF {cpf}.")
            return None

        cursor.execute(
            """
            INSERT INTO pacientes (nome, cpf, data_nascimento, sexo, telefone, endereco)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_paciente;
            """,
            (nome, cpf, data_nascimento, sexo, telefone, endereco),
        )

        id_paciente = cursor.fetchone()[0]
        conn.commit()
        print(f"Paciente '{nome}' cadastrado com sucesso! ID: {id_paciente}")
        return id_paciente

    except Exception as e:
        conn.rollback()
        print(f"Erro ao cadastrar paciente: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def buscar_paciente_por_cpf(cpf):
    conn = obter_conexao()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id_paciente, nome, cpf, data_nascimento, sexo, telefone, endereco
            FROM pacientes
            WHERE cpf = %s
            """,
            (cpf,),
        )

        resultado = cursor.fetchone()
        if not resultado:
            print(f"Nenhum paciente encontrado com o CPF {cpf}.")
            return None

        # Retorna os dados como dicionário para facilitar o uso na interface
        paciente = {
            "id_paciente":      resultado[0],
            "nome":             resultado[1],
            "cpf":              resultado[2],
            "data_nascimento":  resultado[3],
            "sexo":             resultado[4],
            "telefone":         resultado[5],
            "endereco":         resultado[6],
        }
        return paciente

    except Exception as e:
        print(f"Erro ao buscar paciente: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def buscar_comorbidades_do_paciente(id_paciente):
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.id_comorbidade, c.nome, c.pontuacao_extra
            FROM comorbidades c
            INNER JOIN paciente_comorbidade pc ON c.id_comorbidade = pc.id_comorbidade
            WHERE pc.id_paciente = %s
            """,
            (id_paciente,),
        )

        resultados = cursor.fetchall()
        comorbidades = [
            {
                "id_comorbidade": r[0],
                "nome":           r[1],
                "pontuacao_extra": r[2],
            }
            for r in resultados
        ]
        return comorbidades

    except Exception as e:
        print(f"Erro ao buscar comorbidades: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def associar_comorbidade(id_paciente, id_comorbidade):
    conn = obter_conexao()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Verifica se a associação já existe para não duplicar
        cursor.execute(
            """
            SELECT 1 FROM paciente_comorbidade
            WHERE id_paciente = %s AND id_comorbidade = %s
            """,
            (id_paciente, id_comorbidade),
        )
        if cursor.fetchone():
            print("Comorbidade já associada a este paciente.")
            return False

        cursor.execute(
            """
            INSERT INTO paciente_comorbidade (id_paciente, id_comorbidade)
            VALUES (%s, %s);
            """,
            (id_paciente, id_comorbidade),
        )

        conn.commit()
        print("Comorbidade associada com sucesso!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Erro ao associar comorbidade: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def listar_comorbidades_disponiveis():
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_comorbidade, nome, pontuacao_extra FROM comorbidades ORDER BY nome")
        resultados = cursor.fetchall()
        return [
            {
                "id_comorbidade": r[0],
                "nome":           r[1],
                "pontuacao_extra": r[2],
            }
            for r in resultados
        ]

    except Exception as e:
        print(f"Erro ao listar comorbidades: {e}")
        return []

    finally:
        cursor.close()
        conn.close()
