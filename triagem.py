from database import obter_conexao


def processar_triagem(
    id_paciente, id_enfermeiro, lista_id_sintomas, id_comorbidades, consciente
):
    conn = obter_conexao()
    if not conn:
        return False

    try:
        # Cursor para interagirmos com o banco de dados do neon
        cursor = conn.cursor()

        # Se o paciente estiver inconsciente atribuimos diretamente a classificação vermelho
        if not consciente:
            pontuacao_total = 100
            classificacao = "VERMELHO"
            prioridade = 1

        else:
            # Busca a soma dos pontos dos sintomas no banco
            format_sintomas = ",".join("%s" for _ in lista_id_sintomas)
            cursor.execute(
                f"SELECT SUM(pontuacao) FROM sintomas WHERE id_sintomas IN ({format_sintomas})",
                tuple(lista_id_sintomas),
            )
            pontos_sintomas = cursor.fetchone()[0] or 0

            # Busca a soma dos pontos extras das comorbidades do paciente
            pontos_comorbidades = 0
            if id_comorbidades:
                format_comorbidades = ",".join("%s" for _ in id_comorbidades)
                cursor.execute(
                    f"SELECT SUM(pontuacao_extra) FROM comorbidades WHERE id_comorbidade IN ({format_comorbidades})",
                    tuple(id_comorbidades),
                )
                pontos_comorbidades = cursor.fetchone()[0] or 0

            # Bate o total de pontos com a tabela 'regras_classificacao' do SQL
            cursor.execute(
                """
                SELECT classificacao, tabelas
                FROM regras_classificacao
                WHERE %s BETWEEN min_pontos AND max_pontos """,
                (pontuacao_total,),
            )

            regra = cursor.fetchone()
            classificacao = regra[0] if regra else "VERDE"
            prioridade = regra[1] if regra else 4

            # Salva a triagem na tabela 'triagens'
            cursor.execute(
                """
                INSERT INTO triagens (id_paciente, id_enfermeiro, consciente, pontuacao_sintomas, pontuacao_risco, pontuacao_total, prioridade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_triagem;
            """,
                (
                    id_paciente,
                    id_enfermeiro,
                    consciente,
                    pontos_sintomas,
                    pontos_comorbidades,
                    pontuacao_total,
                    classificacao,
                    prioridade,
                ),
            )
            id_triagem = cursor.fetchone()[0]

        # Vincula os sintomas na tabela intermediária (N:N) 'triagem_sintomas'
        for id_sintoma in lista_id_sintomas:
            cursor.execute(
                "INSERT INTO triagem_sintomas (id_triagem, id_sintoma) VALUES (%s, %s);",
                (id_triagem, id_sintoma),
            )

        # Coloca o paciente automaticamente na 'fila_atendimento'
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
            "classificacao": classificacao,
            "prioridade": prioridade,
        }

    except Exception as e:
        conn.rollback()
        print(f"Erro no processo de triagem {e}")
        return None

    finally:
        cursor.close()
        conn.close()
