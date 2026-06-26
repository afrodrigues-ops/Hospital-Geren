-- =====================================================
-- HOSPISYS
-- Sistema de Triagem Hospitalar
-- PostgreSQL / Neon.tech
-- Versão Final — Protocolo de Manchester
-- =====================================================
--
-- MUDANÇA DE MODELO (em relação à versão anterior):
--
-- Antes: triagem por SOMA DE PONTOS de sintomas + comorbidades, comparada
-- contra faixas (min_pontos/max_pontos) em `regras_classificacao`.
--
-- Agora: triagem pelo Protocolo de Manchester real. O enfermeiro escolhe
-- um FLUXOGRAMA (queixa principal, ex: "DOR TORÁCICA"), e dentro dele
-- percorre os DISCRIMINADORES do nível mais urgente (EMERGÊNCIA) para o
-- menos urgente (POUCO URGENTE). O primeiro discriminador confirmado já
-- define a classificação — não soma nada com o resto. Se nenhum
-- discriminador for confirmado, a classificação cai no nível padrão
-- implícito: NÃO URGENTE (azul).
--
-- Comorbidades deixam de dar pontos e passam a ser um AGRAVANTE: podem
-- subir a classificação em no máximo 1 nível, com teto em EMERGÊNCIA
-- (nunca "criam" uma emergência do nada, só empurram um nível mais grave).
-- =====================================================

-- ==========================
-- USUÁRIOS DO SISTEMA
-- ==========================

CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    tipo_usuario VARCHAR(20) NOT NULL
        CHECK (tipo_usuario IN ('ADMIN', 'ENFERMEIRO', 'MEDICO')),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- PACIENTES
-- ==========================

CREATE TABLE pacientes (
    id_paciente SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE NOT NULL,
    sexo VARCHAR(20),
    telefone VARCHAR(20),
    endereco TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- COMORBIDADES
-- ==========================
-- pontuacao_extra foi removida: comorbidade não soma ponto, ela agrava
-- a classificação do Manchester em até 1 nível (regra aplicada em código,
-- ver triagem.py / processar_triagem).

CREATE TABLE comorbidades (
    id_comorbidade SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE paciente_comorbidade (
    id_paciente INTEGER NOT NULL,
    id_comorbidade INTEGER NOT NULL,

    PRIMARY KEY (id_paciente, id_comorbidade),

    FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente)
        ON DELETE CASCADE,

    FOREIGN KEY (id_comorbidade)
        REFERENCES comorbidades(id_comorbidade)
        ON DELETE CASCADE
);

-- ==========================
-- FLUXOGRAMAS (Protocolo de Manchester)
-- ==========================
-- Cada fluxograma é uma queixa principal (ex.: "DOR TORÁCICA",
-- "DISPNEIA EM ADULTO", "AGRESSÃO"). Equivale ao antigo cd_sintoma_avaliacao
-- da planilha de origem (SQLT0482).

CREATE TABLE fluxogramas (
    id_fluxograma INTEGER PRIMARY KEY,  -- mantém o cd_sintoma_avaliacao original da planilha
    nome VARCHAR(150) UNIQUE NOT NULL
);

-- ==========================
-- DISCRIMINADORES
-- ==========================
-- Cada linha é uma pergunta/critério dentro de um fluxograma, associada
-- a um nível de classificação. A ordem dentro do mesmo fluxograma+nível
-- é a ordem de avaliação sugerida (nem sempre estritamente sequencial:
-- ver fluxograma 158, "múltiplas vítimas", onde critérios do mesmo nível
-- são paralelos/alternativos).

CREATE TABLE discriminadores (
    id_discriminador SERIAL PRIMARY KEY,
    id_fluxograma INTEGER NOT NULL REFERENCES fluxogramas(id_fluxograma),
    classificacao VARCHAR(20) NOT NULL
        CHECK (classificacao IN ('EMERGÊNCIA', 'MUITO URGENTE', 'URGENTE', 'POUCO URGENTE')),
    prioridade INTEGER NOT NULL
        CHECK (prioridade BETWEEN 1 AND 4),  -- 1=EMERGÊNCIA ... 4=POUCO URGENTE
    ordem INTEGER NOT NULL,                  -- ordem de avaliação dentro do fluxograma+nível
    pergunta VARCHAR(200) NOT NULL,
    explicacao TEXT
);

CREATE INDEX idx_discriminadores_fluxograma
ON discriminadores(id_fluxograma, prioridade, ordem);

-- ==========================
-- TRIAGENS
-- ==========================
-- pontuacao_sintomas / pontuacao_risco / pontuacao_total saem do modelo de
-- pontos. No lugar, guardamos qual fluxograma e qual discriminador (se
-- algum) foi confirmado, mais a classificação final já considerando o
-- agravamento de comorbidade.

CREATE TABLE triagens (
    id_triagem SERIAL PRIMARY KEY,

    id_paciente INTEGER NOT NULL,
    id_enfermeiro INTEGER NOT NULL,

    data_triagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    consciente BOOLEAN DEFAULT TRUE,

    id_fluxograma INTEGER REFERENCES fluxogramas(id_fluxograma),
    id_discriminador INTEGER REFERENCES discriminadores(id_discriminador),
    -- id_discriminador fica NULL quando nenhum discriminador foi confirmado
    -- (classificação cai no nível padrão implícito: NÃO URGENTE)

    classificacao_base VARCHAR(20) NOT NULL    -- classificação antes do agravante de comorbidade
        CHECK (classificacao_base IN ('EMERGÊNCIA', 'MUITO URGENTE', 'URGENTE', 'POUCO URGENTE', 'NÃO URGENTE')),
    classificacao VARCHAR(20) NOT NULL         -- classificação final (após agravante)
        CHECK (classificacao IN ('EMERGÊNCIA', 'MUITO URGENTE', 'URGENTE', 'POUCO URGENTE', 'NÃO URGENTE')),
    agravado_por_comorbidade BOOLEAN DEFAULT FALSE,
    prioridade INTEGER NOT NULL                -- prioridade final (1=EMERGÊNCIA ... 5=NÃO URGENTE)
        CHECK (prioridade BETWEEN 1 AND 5),

    status VARCHAR(30)
        DEFAULT 'AGUARDANDO_ATENDIMENTO',

    FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente),

    FOREIGN KEY (id_enfermeiro)
        REFERENCES usuarios(id_usuario)
);

-- ==========================
-- RELAÇÃO TRIAGEM/COMORBIDADES CONSIDERADAS
-- ==========================
-- Guarda quais comorbidades do paciente foram de fato levadas em conta
-- nessa triagem específica (pode ser um subconjunto do cadastro geral
-- do paciente).

CREATE TABLE triagem_comorbidades (
    id_triagem INTEGER NOT NULL,
    id_comorbidade INTEGER NOT NULL,

    PRIMARY KEY (id_triagem, id_comorbidade),

    FOREIGN KEY (id_triagem)
        REFERENCES triagens(id_triagem)
        ON DELETE CASCADE,

    FOREIGN KEY (id_comorbidade)
        REFERENCES comorbidades(id_comorbidade)
);

-- ==========================
-- FILA DE ATENDIMENTO
-- ==========================

CREATE TABLE fila_atendimento (
    id_fila SERIAL PRIMARY KEY,

    id_triagem INTEGER UNIQUE NOT NULL,

    prioridade INTEGER NOT NULL,

    hora_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hora_chamada TIMESTAMP,

    status VARCHAR(20)
        DEFAULT 'AGUARDANDO',

    FOREIGN KEY (id_triagem)
        REFERENCES triagens(id_triagem)
        ON DELETE CASCADE
);

-- ==========================
-- ATENDIMENTOS MÉDICOS
-- ==========================

CREATE TABLE atendimentos (
    id_atendimento SERIAL PRIMARY KEY,

    id_triagem INTEGER UNIQUE NOT NULL,
    id_medico INTEGER NOT NULL,

    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,

    diagnostico TEXT,
    observacoes TEXT,

    FOREIGN KEY (id_triagem)
        REFERENCES triagens(id_triagem),

    FOREIGN KEY (id_medico)
        REFERENCES usuarios(id_usuario)
);

-- ==========================
-- AUDITORIA
-- ==========================

CREATE TABLE auditoria (
    id_log SERIAL PRIMARY KEY,

    id_usuario INTEGER,

    acao VARCHAR(100) NOT NULL,
    tabela_afetada VARCHAR(100),
    registro_id INTEGER,

    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
);

-- =====================================================
-- DADOS INICIAIS (que não vêm da planilha)
-- =====================================================

INSERT INTO comorbidades (nome)
VALUES
('Diabetes'),
('Hipertensao'),
('Asma'),
('Cardiopatia');

-- Fluxogramas e discriminadores do Protocolo de Manchester são
-- inseridos pelo script gerar_sql_importacao.py a partir da planilha
-- oficial (ver importacao_manchester.sql).

-- =====================================================
-- ÍNDICES
-- =====================================================

CREATE INDEX idx_triagem_paciente
ON triagens(id_paciente);

CREATE INDEX idx_fila_prioridade
ON fila_atendimento(prioridade);

CREATE INDEX idx_atendimento_medico
ON atendimentos(id_medico);

CREATE INDEX idx_auditoria_usuario
ON auditoria(id_usuario);

-- =====================================================
-- VIEW PARA O PAINEL MÉDICO
-- =====================================================

CREATE VIEW vw_fila_priorizada AS
SELECT
    f.id_fila,
    p.nome AS paciente,
    t.classificacao,
    f.prioridade,
    f.hora_entrada,
    f.status
FROM fila_atendimento f
INNER JOIN triagens t
    ON f.id_triagem = t.id_triagem
INNER JOIN pacientes p
    ON t.id_paciente = p.id_paciente
ORDER BY
    f.prioridade ASC,
    f.hora_entrada ASC;
