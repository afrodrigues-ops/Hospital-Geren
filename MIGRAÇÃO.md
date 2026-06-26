# Migração: triagem por pontos → Protocolo de Manchester real

## O que mudou e por quê

O modelo antigo (`sintomas` + `regras_classificacao`) somava pontos de
sintomas e comorbidades e comparava contra faixas (min_pontos/max_pontos).
A planilha real do Manchester (SQLT0482) não funciona assim: o enfermeiro
escolhe um **fluxograma** (queixa principal) e percorre os
**discriminadores** do nível mais urgente (EMERGÊNCIA) para o menos
urgente (POUCO URGENTE) — o primeiro confirmado já decide a
classificação, sem somar nada com o resto. Quando nenhum discriminador é
confirmado, a classificação cai no nível padrão implícito: **NÃO
URGENTE**.

Comorbidades deixaram de dar pontos. Agora funcionam como agravante: se o
paciente tem alguma comorbidade cadastrada na triagem, a classificação
sobe **no máximo 1 nível**, com teto em EMERGÊNCIA (nunca passa disso).

## Arquivos deste pacote

| Arquivo | O que é |
|---|---|
| `schema.sql` | Schema completo novo do banco (substitui o `sintomas`/`regras_classificacao` por `fluxogramas`/`discriminadores`; tabelas que não mudaram de estrutura — usuários, pacientes, fila, atendimentos, auditoria — ficam iguais) |
| `gerar_sql_importacao.py` | Script Python que lê a planilha oficial do Manchester e gera o SQL de importação |
| `importacao_manchester.sql` | SQL já gerado a partir da sua planilha (55 fluxogramas, 1325 discriminadores) — pronto pra rodar |
| `triagem.py` | Reescrito: nova lógica de classificação por fluxograma+discriminador, e o agravante de comorbidade |
| `app.py` | Menu de triagem reescrito: lista fluxogramas, percorre discriminadores nível a nível, marca comorbidades |
| `paciente.py` | Ajustado: comorbidade não tem mais `pontuacao_extra` |
| `database.py`, `auth.py`, `misc.py`, `main.py`, `lista_encadeada.py`, `tabela_hash.py`, `requirements.txt` | Sem mudanças de estrutura, copiados para manter o pacote completo e pronto pra rodar |

## Como aplicar

1. **Banco zerado / ambiente novo**: rode `schema.sql` e depois
   `importacao_manchester.sql` direto no Postgres (Neon.tech), na ordem.

2. **Banco já existente com o modelo antigo**: você vai precisar dropar
   `sintomas`, `regras_classificacao` e `triagem_sintomas` (e os dados de
   `triagens` que referenciam o modelo antigo, se não quiser manter
   histórico antigo incompatível), e então rodar a parte de
   `fluxogramas`/`discriminadores`/`triagem_comorbidades` do
   `schema.sql`, seguida de `importacao_manchester.sql`. Não escrevi um
   script de migração automática para isso porque depende de você decidir
   o que fazer com o histórico de triagens já registradas — me avise se
   quiser que eu monte esse script também.

3. Regerar o SQL de importação a qualquer momento (ex.: planilha
   atualizada):
   ```bash
   python gerar_sql_importacao.py caminho/para/planilha.xlsx importacao_manchester.sql
   ```

## Validações já feitas

- O SQL de importação foi executado contra um banco de teste e os números
  batem exatamente com a planilha original: 55 fluxogramas, 1325
  discriminadores, distribuição por nível (EMERGÊNCIA: 256, MUITO
  URGENTE: 471, URGENTE: 379, POUCO URGENTE: 219).
- A lógica de `classificar_por_discriminador` e
  `aplicar_agravante_comorbidade` foi testada isoladamente (vários
  discriminadores confirmados ao mesmo tempo → vale o mais urgente;
  nenhum confirmado → NÃO URGENTE; comorbidade nunca passa de EMERGÊNCIA).
- Teste de integração ponta a ponta (schema + dados reais + inserção de
  triagem + fila de atendimento) rodado com sucesso usando o fluxograma
  real "DOR TORÁCICA".

## Atenção: 1 inconsistência na planilha de origem

O fluxograma 158 ("SITUAÇÃO DE MÚLTIPLAS VÍTIMAS — AVALIAÇÃO PRIMÁRIA")
repete `nr_ordem_pergunta = 1` para 3 perguntas diferentes dentro do
nível EMERGÊNCIA (são critérios paralelos de triagem em massa, não
sequenciais). Por isso o script de importação **não** usa
`nr_ordem_pergunta` como identificador único — ele recalcula a ordem real
de inserção por fluxograma+nível. Os dados desse fluxograma foram
importados normalmente, como você pediu.
