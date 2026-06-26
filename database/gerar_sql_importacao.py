"""
gerar_sql_importacao.py

Lê a planilha "sintoma_pergunta_classificação.xlsx" (export SQLT0482 do
Protocolo de Classificação de Risco de Manchester) e gera um arquivo .sql
com os INSERTs para popular as tabelas novas `fluxogramas` e
`discriminadores`.

Uso:
    python gerar_sql_importacao.py caminho/para/planilha.xlsx saida.sql

Regras de leitura aplicadas (validadas manualmente na planilha de origem):
  - 55 fluxogramas distintos (cd_sintoma_avaliacao / ds_sintoma)
  - 1325 linhas de discriminadores no total
  - cd_classificacao é uma tabela de domínio FIXA e global do Manchester
    (15=EMERGÊNCIA, 16=MUITO URGENTE, 17=URGENTE, 18=POUCO URGENTE),
    não varia por fluxograma — por isso mapeamos direto para o nosso
    enum de prioridade (1 a 4) e ignoramos o cd_classificacao numérico
    em si, guardando apenas o nome do nível.
  - nr_ordem_pergunta NÃO é confiável como identificador único dentro de
    fluxograma+nível: o fluxograma 158 (situação de múltiplas vítimas)
    repete a ordem 1 para 3 perguntas distintas (são critérios paralelos
    de triagem em massa, não sequenciais). Por isso a ordem real de
    inserção (enumerate) é usada como `ordem`, e nr_ordem_pergunta vira
    só um metadado de referência dentro de `pergunta` (não é PK/UNIQUE).
"""

import sys
from collections import OrderedDict

import openpyxl

# Mapa fixo de classificação do Manchester -> (nome, prioridade 1=mais urgente)
NIVEL_PRIORIDADE = {
    "EMERGÊNCIA": 1,
    "MUITO URGENTE": 2,
    "URGENTE": 3,
    "POUCO URGENTE": 4,
}


def escapar(texto: str) -> str:
    """Escapa aspas simples para uso seguro em literais SQL."""
    if texto is None:
        return ""
    return texto.replace("'", "''")


def gerar_sql(caminho_planilha: str, caminho_saida: str) -> None:
    wb = openpyxl.load_workbook(caminho_planilha, data_only=True)
    ws = wb["SQLT0482"]

    linhas = list(ws.iter_rows(min_row=2, values_only=True))

    # 1) Coleta fluxogramas únicos, preservando a ordem de primeira aparição
    fluxogramas = OrderedDict()  # cd_sintoma_avaliacao -> ds_sintoma
    for r in linhas:
        cd_sintoma, ds_sintoma = r[0], r[1]
        if cd_sintoma not in fluxogramas:
            fluxogramas[cd_sintoma] = ds_sintoma.strip()

    # 2) Monta os discriminadores, calculando a ordem real de inserção
    #    por (fluxograma, nível), já que nr_ordem_pergunta pode repetir.
    contador_ordem = {}  # (cd_sintoma, ds_tipo_risco) -> próximo número de ordem
    discriminadores = []  # lista de dicts prontos pra gerar o INSERT

    for r in linhas:
        cd_sintoma, ds_sintoma, cd_classificacao, ds_tipo_risco, nr_ordem_pergunta, ds_pergunta, ds_explicacao = r

        nivel = ds_tipo_risco.strip().upper()
        if nivel not in NIVEL_PRIORIDADE:
            raise ValueError(f"Nível de risco desconhecido na planilha: {nivel!r}")

        chave = (cd_sintoma, nivel)
        contador_ordem.setdefault(chave, 0)
        contador_ordem[chave] += 1
        ordem_real = contador_ordem[chave]

        discriminadores.append(
            {
                "id_fluxograma": cd_sintoma,
                "classificacao": nivel,
                "prioridade": NIVEL_PRIORIDADE[nivel],
                "ordem": ordem_real,
                "nr_ordem_pergunta_origem": nr_ordem_pergunta,
                "pergunta": ds_pergunta.strip(),
                "explicacao": (ds_explicacao or "").strip(),
            }
        )

    # 3) Gera o SQL
    out = []
    out.append("-- =====================================================")
    out.append("-- Importação de dados do Protocolo de Manchester")
    out.append(f"-- Gerado a partir de: {caminho_planilha}")
    out.append(f"-- Fluxogramas: {len(fluxogramas)} | Discriminadores: {len(discriminadores)}")
    out.append("-- =====================================================")
    out.append("")
    out.append("BEGIN;")
    out.append("")

    # --- fluxogramas ---
    out.append("-- ==========================")
    out.append("-- FLUXOGRAMAS")
    out.append("-- ==========================")
    out.append("INSERT INTO fluxogramas (id_fluxograma, nome) VALUES")
    valores_fluxo = []
    for cd_sintoma, nome in fluxogramas.items():
        valores_fluxo.append(f"    ({cd_sintoma}, '{escapar(nome)}')")
    out.append(",\n".join(valores_fluxo) + "\nON CONFLICT (id_fluxograma) DO NOTHING;")
    out.append("")

    # --- discriminadores ---
    out.append("-- ==========================")
    out.append("-- DISCRIMINADORES")
    out.append("-- ==========================")
    out.append(
        "INSERT INTO discriminadores "
        "(id_fluxograma, classificacao, prioridade, ordem, pergunta, explicacao) VALUES"
    )
    valores_disc = []
    for d in discriminadores:
        valores_disc.append(
            "    ({id_fluxograma}, '{classificacao}', {prioridade}, {ordem}, "
            "'{pergunta}', '{explicacao}')".format(
                id_fluxograma=d["id_fluxograma"],
                classificacao=d["classificacao"],
                prioridade=d["prioridade"],
                ordem=d["ordem"],
                pergunta=escapar(d["pergunta"]),
                explicacao=escapar(d["explicacao"]),
            )
        )
    # PostgreSQL aceita um INSERT gigante com múltiplos VALUES; para 1325 linhas
    # isso é tranquilo, mas quebramos em lotes de 200 pra ficar legível e
    # evitar um único statement gigantesco demais.
    LOTE = 200
    for i in range(0, len(valores_disc), LOTE):
        bloco = valores_disc[i : i + LOTE]
        if i > 0:
            out.append("")
            out.append(
                "INSERT INTO discriminadores "
                "(id_fluxograma, classificacao, prioridade, ordem, pergunta, explicacao) VALUES"
            )
        terminador = ";" if i + LOTE >= len(valores_disc) else ";"
        out.append(",\n".join(bloco) + terminador)

    out.append("")
    out.append("COMMIT;")
    out.append("")

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"OK: {len(fluxogramas)} fluxogramas e {len(discriminadores)} discriminadores")
    print(f"Arquivo gerado em: {caminho_saida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python gerar_sql_importacao.py <planilha.xlsx> <saida.sql>")
        sys.exit(1)
    gerar_sql(sys.argv[1], sys.argv[2])
