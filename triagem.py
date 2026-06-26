from database import obter_conexao


def processar_triagem(id_paciente, id_enfermeiro, lista_id_sintomas, id_comorbidades, consciente):
    conn = obter_conexao()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Se o paciente estiver inconsciente, já vai direto para VERMELHO
        if not consciente:
            pontuacao_total = 100
            classificacao = "VERMELHO"
            prioridade = 1

        else:
            # CORREÇÃO 1: era "id_sintomas", o nome certo da coluna é "id_sintoma"
            format_sintomas = ",".join("%s" for _ in lista_id_sintomas)
            cursor.execute(
                f"SELECT SUM(pontuacao) FROM sintomas WHERE id_sintoma IN ({format_sintomas})",
                tuple(lista_id_sintomas),
            )
            pontos_sintomas = cursor.fetchone()[0] or 0

            # Busca pontos extras das comorbidades
            pontos_comorbidades = 0
            if id_comorbidades:
                format_comorbidades = ",".join("%s" for _ in id_comorbidades)
                cursor.execute(
                    f"SELECT SUM(pontuacao_extra) FROM comorbidades WHERE id_comorbidade IN ({format_comorbidades})",
                    tuple(id_comorbidades),
                )
                pontos_comorbidades = cursor.fetchone()[0] or 0

            # CORREÇÃO 2: pontuacao_total não existia antes de ser usada na query abaixo
            pontuacao_total = pontos_sintomas + pontos_comorbidades

            # CORREÇÃO 3: era "tabelas", o nome certo da coluna é "prioridade"
            cursor.execute(
                """
                SELECT classificacao, prioridade
                FROM regras_classificacao
                WHERE %s BETWEEN min_pontos AND max_pontos
                """,
                (pontuacao_total,),
            )

            regra = cursor.fetchone()
            classificacao = regra[0] if regra else "VERDE"
            prioridade = regra[1] if regra else 4

        # CORREÇÃO 4: faltava o campo "classificacao" no INSERT e o número de %s estava errado
        # Também movido para fora do bloco "else" para funcionar no caso inconsciente também
        cursor.execute(
            """
            INSERT INTO triagens (
                id_paciente, id_enfermeiro, consciente,
                pontuacao_sintomas, pontuacao_risco, pontuacao_total,
                classificacao, prioridade
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_triagem;
            """,
            (
                id_paciente,
                id_enfermeiro,
                consciente,
                pontos_sintomas if consciente else 0,
                pontos_comorbidades if consciente else 0,
                pontuacao_total,
                classificacao,
                prioridade,
            ),
        )
        id_triagem = cursor.fetchone()[0]

        # Vincula os sintomas selecionados na triagem (tabela N:N)
        for id_sintoma in lista_id_sintomas:
            cursor.execute(
                "INSERT INTO triagem_sintomas (id_triagem, id_sintoma) VALUES (%s, %s);",
                (id_triagem, id_sintoma),
            )

        # Insere o paciente na fila de atendimento automaticamente
        cursor.execute(
            """
            INSERT INTO fila_atendimento (id_triagem, prioridade, status)
            VALUES (%s, %s, 'AGUARDANDO');
            """,
            (id_triagem, prioridade),
        )

        conn.commit()
        return {
            "status": "sucesso",
            "id_triagem": id_triagem,
            "classificacao": classificacao,
            "prioridade": prioridade,
            "pontuacao_total": pontuacao_total,
        }

    except Exception as e:
        conn.rollback()
        print(f"Erro no processo de triagem: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def listar_sintomas_disponiveis():
    # ATENÇÃO: assume que a tabela "sintomas" tem uma coluna "nome" (igual a
    # "comorbidades"). Se o nome da coluna no seu banco for diferente, ajuste
    # o SELECT abaixo.
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_sintoma, nome, pontuacao FROM sintomas ORDER BY nome")
        resultados = cursor.fetchall()
        return [
            {
                "id_sintoma": r[0],
                "nome": r[1],
                "pontuacao": r[2],
            }
            for r in resultados
        ]

    except Exception as e:
        print(f"Erro ao listar sintomas: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def listar_fila_atendimento():
    # Lista os pacientes que estão aguardando atendimento, do mais urgente
    # para o menos urgente (prioridade 1 = mais urgente).
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.nome, p.cpf, t.classificacao, f.prioridade, f.status
            FROM fila_atendimento f
            INNER JOIN triagens t ON t.id_triagem = f.id_triagem
            INNER JOIN pacientes p ON p.id_paciente = t.id_paciente
            WHERE f.status = 'AGUARDANDO'
            ORDER BY f.prioridade ASC
            """
        )
        resultados = cursor.fetchall()
        return [
            {
                "nome": r[0],
                "cpf": r[1],
                "classificacao": r[2],
                "prioridade": r[3],
                "status": r[4],
            }
            for r in resultados
        ]

    except Exception as e:
        print(f"Erro ao listar fila de atendimento: {e}")
        return []

    finally:
        cursor.close()
        conn.close()
