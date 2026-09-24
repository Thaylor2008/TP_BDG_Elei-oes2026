# -*- coding: utf-8 -*-
"""
Carga da tabela unificada (IPS Brasil x IDEB) no PostgreSQL/PostGIS da disciplina.

Servidor: 150.164.2.42:5432 / banco bdg2026 / schema geodata (ver PDF de especificacao)
Tabela criada: geodata.thaylor_verteiro_seguranca_educacao
  - cd_mun eh a chave de integracao com geodata.munic (codigo IBGE do municipio)
  - a tabela em si NAO tem geometria propria: as analises espaciais devem fazer
    JOIN com geodata.munic pelo cd_mun para obter o poligono do municipio.
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

CONN = dict(host="150.164.2.42", port=5432, dbname="bdg2026", user="turma2026", password="turma")
TABELA = "thaylor_verteiro_seguranca_educacao"

df = pd.read_csv(
    "Dados processados/grupo_seguranca_educacao.csv",
    dtype={
        "cd_mun": str, "cd_rgi": str, "cd_rgint": str, "cd_tse": "Int64",
        "ideb_anos_iniciais_ano_ref": "Int64", "ideb_anos_finais_ano_ref": "Int64",
        "ideb_ensino_medio_ano_ref": "Int64",
    },
)


def to_native(v):
    """Converte tipos numpy/pandas para tipos nativos do Python e NaN/NaT/pd.NA para None.
    IMPORTANTE: nunca reatribuir o resultado a uma coluna do DataFrame (df[c] = df[c].map(...)) --
    o pandas reinfere o dtype da coluna na reatribuicao e converte None de volta para NaN
    (e Int64 nulavel de volta para float64), o que fazia o psycopg2 tentar inserir NaN numa
    coluna integer e estourar 'integer out of range'. Por isso a conversao e aplicada apenas
    na hora de montar as tuplas de insercao, abaixo."""
    if v is None:
        return None
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


print(f"linhas a carregar: {len(df)} | colunas: {len(df.columns)}")

ddl = f"""
DROP TABLE IF EXISTS geodata.{TABELA};
CREATE TABLE geodata.{TABELA} (
    cd_mun                              varchar(7) PRIMARY KEY,
    nm_mun                              varchar(120),
    sigla_uf                            varchar(2),
    cd_rgi                               varchar(10),
    cd_rgint                            varchar(10),
    area_km2                            double precision,
    cd_tse                              integer,
    populacao_2025                      double precision,
    pib_per_capita                      double precision,
    ips_geral                           double precision,
    ips_seguranca_pessoal               double precision,
    ips_homicidios                      double precision,
    ips_assassinatos_jovens             double precision,
    ips_assassinatos_mulheres           double precision,
    ips_mortes_transito                 double precision,
    ips_violencia_mulheres              double precision,
    ips_violencia_negros                double precision,
    ips_violencia_indigenas             double precision,
    ips_acesso_conhecimento_basico      double precision,
    ips_acesso_educ_superior            double precision,
    ips_abandono_fundamental            double precision,
    ips_abandono_medio                  double precision,
    ips_distorcao_idade_serie_medio     double precision,
    ips_evasao_medio                    double precision,
    ips_ideb_fundamental_ref            double precision,
    ips_reprovacao_medio                double precision,
    ips_nota_mediana_enem               double precision,
    ips_empregados_ensino_superior      double precision,
    ideb_anos_iniciais                  double precision,
    ideb_anos_iniciais_ano_ref          integer,
    ideb_anos_finais                    double precision,
    ideb_anos_finais_ano_ref            integer,
    ideb_ensino_medio                   double precision,
    ideb_ensino_medio_ano_ref           integer
);
COMMENT ON TABLE geodata.{TABELA} IS
    'Grupo Seguranca Publica x Educacao - IPS Brasil 2026 (nome+UF pareado ao cd_mun oficial) '
    'integrado ao IDEB/INEP 2025 (Anos Iniciais, Anos Finais, Ensino Medio, rede Publica). '
    'Chave cd_mun compativel com geodata.munic.cd_mun para analises espaciais (fazer JOIN).';
"""

cols = list(df.columns)
placeholders = ", ".join(cols)
insert_sql = f"INSERT INTO geodata.{TABELA} ({placeholders}) VALUES %s"

conn = psycopg2.connect(connect_timeout=15, **CONN)
try:
    with conn.cursor() as cur:
        cur.execute(ddl)
        rows = [tuple(to_native(v) for v in r) for r in df[cols].itertuples(index=False, name=None)]
        execute_values(cur, insert_sql, rows, page_size=1000)
    conn.commit()
    print("Carga concluida e commitada.")

    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM geodata.{TABELA};")
        print("linhas na tabela:", cur.fetchone()[0])
        cur.execute(f"""
            SELECT m.cd_mun, t.ips_geral, t.ideb_anos_iniciais
            FROM geodata.{TABELA} t
            JOIN geodata.munic m ON m.cd_mun = t.cd_mun
            ORDER BY t.ips_geral DESC NULLS LAST
            LIMIT 3;
        """)
        print("checagem de JOIN com geodata.munic (top 3 IPS geral):")
        for r in cur.fetchall():
            print(" ", r)
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
