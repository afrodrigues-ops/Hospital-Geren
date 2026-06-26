from database import obter_conexao

# Mapa de classificação -> prioridade numérica (1 = mais urgente).
# NÃO URGENTE é o nível padrão implícito quando nenhum discriminador do
# fluxograma é confirmado pelo enfermeiro.
NIVEL_PRIORIDADE = {
    "EMERGÊNCIA": 1,
    "MUITO URGENTE": 2,
    "URGENTE": 3,
    "POUCO URGENTE": 4,
    "NÃO URGENTE": 5,
}
PRIORIDADE_NIVEL = {v: k for k, v in NIVEL_PRIORIDADE.items()}

NAO_URGENTE = "NÃO URGENTE"
PRIORIDADE_NAO_URGENTE = NIVEL_PRIORIDADE[NAO_URGENTE]


def listar_fluxogramas_disponiveis():
    """Lista todos os fluxogramas (queixas principais) do Protocolo de Manchester."""
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_fluxograma, nome FROM fluxogramas ORDER BY nome")
        resultados = cursor.fetchall()
        return [{"id_fluxograma": r[0], "nome": r[1]} for r in resultados]

    except Exception as e:
        print(f"Erro ao listar fluxogramas: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def listar_discriminadores_do_fluxograma(id_fluxograma):
    """
    Retorna os discriminadores de um fluxograma já ordenados do nível mais
    urgente para o menos urgente (EMERGÊNCIA -> POUCO URGENTE), e dentro de
    cada nível na ordem de avaliação sugerida pelo protocolo.
    """
    conn = obter_conexao()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id_discriminador, classificacao, prioridade, ordem, pergunta, explicacao
            FROM discriminadores
            WHERE id_fluxograma = %s
            ORDER BY prioridade ASC, ordem ASC
            """,
            (id_fluxograma,),
        )
        resultados = cursor.fetchall()
        return [
            {
                "id_discriminador": r[0],
                "classificacao": r[1],
                "prioridade": r[2],
                "ordem": r[3],
                "pergunta": r[4],
                "explicacao": r[5],
            }
            for r in resultados
        ]

    except Exception as e:
        print(f"Erro ao listar discriminadores: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def aplicar_agravante_comorbidade(classificacao_base):
    """
    Regra de negócio combinada: comorbidade não soma ponto, ela AGRAVA a
    classificação em no máximo 1 nível, com teto em EMERGÊNCIA (nunca passa
    disso, mesmo com várias comorbidades).

    Retorna (classificacao_final, prioridade_final).
    """
    prioridade_base = NIVEL_PRIORIDADE[classificacao_base]
    prioridade_final = max(1, prioridade_base - 1)
    return PRIORIDADE_NIVEL[prioridade_final], prioridade_final


def classificar_por_discriminador(lista_id_discriminadores_confirmados, discriminadores_do_fluxograma):
    """
    Aplica a lógica real do Manchester: dentre os discriminadores que o
    enfermeiro confirmou, vale o de prioridade mais alta (menor número),
    já que o protocolo é avaliado do nível mais urgente para o menos
    urgente e o PRIMEIRO confirmado decide — não soma nada com o resto.

    Se nada foi confirmado, classificação cai em NÃO URGENTE.

    Retorna (classificacao_base, id_discriminador_decisivo_ou_None).
    """
    if not lista_id_discriminadores_confirmados:
        return NAO_URGENTE, None

    confirmados = [
        d for d in discriminadores_do_fluxograma
        if d["id_discriminador"] in lista_id_discriminadores_confirmados
    ]
    if not confirmados:
        return NAO_URGENTE, None

    # discriminadores_do_fluxograma já vem ordenado por prioridade ASC, ordem ASC
    # (prioridade 1 = EMERGÊNCIA = mais urgente), então o primeiro confirmado
    # nessa ordem é o decisivo.
    decisivo = min(confirmados, key=lambda d: (d["prioridade"], d["ordem"]))
    return decisivo["classificacao"], decisivo["id_discriminador"]


def processar_triagem(id_paciente, id_enfermeiro, id_fluxograma,
                       lista_id_discriminadores_confirmados, id_comorbidades, consciente):
    """
    Processa a triagem pelo Protocolo de Manchester.

    - Se o paciente está inconsciente, classificação automática é
      EMERGÊNCIA (prioridade 1), sem precisar percorrer discriminadores.
    - Caso contrário, usa o fluxograma escolhido: o primeiro discriminador
      confirmado (do nível mais urgente para o menos urgente) decide a
      classificação base. Se nenhum for confirmado, cai em NÃO URGENTE.
    - Comorbidades presentes agravam a classificação base em até 1 nível,
      com teto em EMERGÊNCIA.
    """
    conn = obter_conexao()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        id_discriminador_decisivo = None

        if not consciente:
            classificacao_base = "EMERGÊNCIA"
        else:
            discriminadores_do_fluxograma = listar_discriminadores_do_fluxograma(id_fluxograma)
            classificacao_base, id_discriminador_decisivo = classificar_por_discriminador(
                lista_id_discriminadores_confirmados, discriminadores_do_fluxograma
            )

        agravado = False
        if id_comorbidades:
            classificacao_final, prioridade_final = aplicar_agravante_comorbidade(classificacao_base)
            agravado = classificacao_final != classificacao_base
        else:
            classificacao_final = classificacao_base
            prioridade_final = NIVEL_PRIORIDADE[classificacao_base]

        cursor.execute(
            """
            INSERT INTO triagens (
                id_paciente, id_enfermeiro, consciente,
                id_fluxograma, id_discriminador,
                classificacao_base, classificacao,
                agravado_por_comorbidade, prioridade
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_triagem;
            """,
            (
                id_paciente,
                id_enfermeiro,
                consciente,
                id_fluxograma if consciente else None,
                id_discriminador_decisivo,
                classificacao_base,
                classificacao_final,
                agravado,
                prioridade_final,
            ),
        )
        id_triagem = cursor.fetchone()[0]

        # Vincula as comorbidades consideradas nessa triagem (tabela N:N)
        for id_comorbidade in (id_comorbidades or []):
            cursor.execute(
                "INSERT INTO triagem_comorbidades (id_triagem, id_comorbidade) VALUES (%s, %s);",
                (id_triagem, id_comorbidade),
            )

        # Insere o paciente na fila de atendimento automaticamente
        cursor.execute(
            """
            INSERT INTO fila_atendimento (id_triagem, prioridade, status)
            VALUES (%s, %s, 'AGUARDANDO');
            """,
            (id_triagem, prioridade_final),
        )

        conn.commit()
        return {
            "status": "sucesso",
            "id_triagem": id_triagem,
            "classificacao_base": classificacao_base,
            "classificacao": classificacao_final,
            "agravado_por_comorbidade": agravado,
            "prioridade": prioridade_final,
        }

    except Exception as e:
        conn.rollback()
        print(f"Erro no processo de triagem: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def listar_fila_atendimento():
    # Lista os pacientes que estão aguardando atendimento, do mais urgente
    # para o menos urgente (prioridade 1 = EMERGÊNCIA, mais urgente).
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
            ORDER BY f.prioridade ASC, f.hora_entrada ASC
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
