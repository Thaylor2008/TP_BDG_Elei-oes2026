# -*- coding: utf-8 -*-
"""
ETL - Trabalho Pratico BDG 2026 - Grupo Seguranca Publica (IPS Brasil) x Educacao (IDEB/INEP)

Junta:
  - Dados brutos/IPS Brasil 2026 - Tabela de Dados_Brasil.csv   (indicadores IPS, chave: nome do municipio + UF)
  - Dados brutos/divulgacao_anos_iniciais_municipios_2025.xlsx  (IDEB Anos Iniciais, chave: CO_MUNICIPIO = cd_mun IBGE)
  - Dados brutos/divulgacao_anos_finais_municipios_2025.xlsx    (IDEB Anos Finais,  chave: CO_MUNICIPIO = cd_mun IBGE)
  - Dados brutos/divulgacao_ensino_medio_municipios_2025.xlsx   (IDEB Ensino Medio,  chave: CO_MUNICIPIO = cd_mun IBGE)

Usa como referencia oficial de codigos IBGE a tabela geodata.munic do banco compartilhado da
disciplina (extraida previamente para Dados brutos/ref/munic_ref.csv), pois o IPS Brasil nao
traz o codigo IBGE do municipio -- apenas nome + UF. O pareamento nome->cd_mun e feito por
normalizacao de string (maiusculas, sem acento, sem pontuacao).

Saida:
  - Dados processados/grupo_seguranca_educacao.csv   -> tabela unificada, uma linha por municipio (cd_mun)
  - Dados processados/estatisticas_descritivas.csv    -> estatisticas descritivas das variaveis selecionadas
  - Dados processados/log_pareamento_ips.csv          -> log de matching nome->cd_mun (para auditoria/relatorio)
"""
import re
import unicodedata
import pandas as pd

RAW = "Dados brutos"
OUT = "Dados processados"

# --------------------------------------------------------------------------------------
# 1. Referencia oficial de municipios (extraida de geodata.munic)
# --------------------------------------------------------------------------------------
ref = pd.read_csv(f"{RAW}/ref/munic_ref.csv", dtype={"cd_mun": str, "cd_rgi": str, "cd_rgint": str, "cd_tse": "Int64"})

# Remove os 2 poligonos hidrograficos do RS que nao sao municipios (ver PDF de especificacao,
# secao "Problemas", itens 1 e 2: codigos 4300001 e 4300002 - Lagoa Mirim e Lagoa dos Patos)
ref = ref[~ref["cd_mun"].isin(["4300001", "4300002"])].copy()
print(f"[ref] municipios de referencia (geodata.munic, excl. corpos d'agua RS): {len(ref)}")


def normaliza(txt: str) -> str:
    """Maiusculas, sem acento, sem pontuacao, espacos colapsados -- para casar nomes de municipio."""
    if pd.isna(txt):
        return ""
    txt = str(txt).strip().upper()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Z0-9 ]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


ref["chave"] = ref["nm_mun"].map(normaliza) + "/" + ref["sigla_uf"].str.upper()
# nao deve haver chave duplicada na referencia oficial
dup_ref = ref[ref.duplicated("chave", keep=False)]
if len(dup_ref):
    print("[ref] ATENCAO - chaves duplicadas na referencia:", dup_ref["chave"].tolist())

ref_map = ref.set_index("chave")["cd_mun"].to_dict()

# --------------------------------------------------------------------------------------
# 2. IPS Brasil (indicadores de seguranca publica e qualidade de vida)
# --------------------------------------------------------------------------------------
ips = pd.read_csv(f"{RAW}/IPS Brasil 2026 - Tabela de Dados_Brasil.csv", encoding="utf-8-sig")
ips.columns = [c.strip() for c in ips.columns]
print(f"[ips] linhas brutas: {len(ips)}")

ips["chave"] = ips["Município"].map(normaliza) + "/" + ips["UF"].str.upper()
ips["cd_mun"] = ips["chave"].map(ref_map)

pareados = ips["cd_mun"].notna().sum()
print(f"[ips] pareados por nome+UF na 1a passada: {pareados}/{len(ips)}")

# 2a. Segunda passada para os nao pareados: casar removendo termos genericos (D', DE, DO, DA, DOS, DAS)
nao_pareados = ips[ips["cd_mun"].isna()].copy()
if len(nao_pareados):
    ref_map_loose = {}
    for chave, cd in ref_map.items():
        nome, uf = chave.rsplit("/", 1)
        nome_loose = re.sub(r"\b(DE|DO|DA|DOS|DAS|D)\b", "", nome)
        nome_loose = re.sub(r"\s+", " ", nome_loose).strip()
        ref_map_loose[f"{nome_loose}/{uf}"] = cd

    def chave_loose(row):
        nome = re.sub(r"\b(DE|DO|DA|DOS|DAS|D)\b", "", row["Município"] and normaliza(row["Município"]))
        nome = re.sub(r"\s+", " ", nome).strip()
        return f"{nome}/{row['UF'].upper()}"

    nao_pareados["chave_loose"] = nao_pareados.apply(chave_loose, axis=1)
    nao_pareados["cd_mun"] = nao_pareados["chave_loose"].map(ref_map_loose)
    ips.loc[nao_pareados.index, "cd_mun"] = nao_pareados["cd_mun"]

pareados2 = ips["cd_mun"].notna().sum()
print(f"[ips] pareados apos 2a passada (sem preposicoes): {pareados2}/{len(ips)}")

# 2b. Correcoes manuais para nomes do IPS Brasil que divergem do nome oficial IBGE
#     (grafia diferente ou nome abreviado) -- identificadas por inspecao dos nao pareados.
correcoes_manuais = {
    ("GRACHO CARDOSO", "SE"): "2802601",   # oficial: Graccho Cardoso
    ("ARES", "RN"): "2401206",             # oficial: Arez
    ("ACU", "RN"): "2400208",              # oficial: Assu
    ("SAO LUIZ", "RR"): "1400605",         # oficial: Sao Luiz do Anaua
}
for idx, row in ips[ips["cd_mun"].isna()].iterrows():
    chave_manual = (normaliza(row["Município"]), row["UF"].upper())
    if chave_manual in correcoes_manuais:
        ips.loc[idx, "cd_mun"] = correcoes_manuais[chave_manual]

pareados3 = ips["cd_mun"].notna().sum()
print(f"[ips] pareados apos correcoes manuais: {pareados3}/{len(ips)}")

# Log de auditoria do pareamento (usado na secao de qualidade/limitacoes do relatorio)
log = ips[["Município", "UF", "chave", "cd_mun"]].copy()
log["status"] = log["cd_mun"].notna().map({True: "OK", False: "NAO PAREADO"})
log.to_csv(f"{OUT}/log_pareamento_ips.csv", index=False, encoding="utf-8-sig")

restantes = ips[ips["cd_mun"].isna()]
if len(restantes):
    print(f"[ips] municipios NAO pareados (ficam fora da tabela unificada): {len(restantes)}")
    print(restantes[["Município", "UF"]].to_string(index=False))

ips = ips[ips["cd_mun"].notna()].copy()

# Checa duplicidade de cd_mun apos pareamento (nao deveria ocorrer)
dup_ips = ips[ips.duplicated("cd_mun", keep=False)]
if len(dup_ips):
    print("[ips] ATENCAO - cd_mun duplicado apos pareamento:")
    print(dup_ips[["Município", "UF", "cd_mun"]].to_string(index=False))

# Colunas do IPS relevantes ao tema (Seguranca Publica) + contexto socioeconomico
ips_cols = {
    "cd_mun": "cd_mun",
    "Índice de Progresso Social": "ips_geral",
    "POPULAÇÃO 2025": "populacao_2025",
    "PIB PER CAPITA": "pib_per_capita",
    "Segurança Pessoal": "ips_seguranca_pessoal",
    "Homicídios": "ips_homicidios",
    "Assassinatos de Jovens": "ips_assassinatos_jovens",
    "Assassinatos de Mulheres": "ips_assassinatos_mulheres",
    "Mortes por Acidentes de Transporte": "ips_mortes_transito",
    "Violência Contra Mulheres": "ips_violencia_mulheres",
    "Violência Contra Negros": "ips_violencia_negros",
    "Violência Contra Indígenas": "ips_violencia_indigenas",
    "Acesso ao Conhecimento Básico": "ips_acesso_conhecimento_basico",
    "Acesso à Educação Superior": "ips_acesso_educ_superior",
    "Abandono no Ensino Fundamental": "ips_abandono_fundamental",
    "Abandono no Ensino Médio": "ips_abandono_medio",
    "Distorção Idade-Série no Ensino Médio": "ips_distorcao_idade_serie_medio",
    "Evasão no Ensino Médio": "ips_evasao_medio",
    "Ideb Ensino Fundamental": "ips_ideb_fundamental_ref",
    "Reprovação Escolar no Ensino Médio": "ips_reprovacao_medio",
    "Nota Mediana no Enem": "ips_nota_mediana_enem",
    "Empregados com Ensino Superior": "ips_empregados_ensino_superior",
}
ips_sel = ips[list(ips_cols.keys())].rename(columns=ips_cols)

# --------------------------------------------------------------------------------------
# 3. IDEB (INEP) - Anos Iniciais, Anos Finais e Ensino Medio - rede "Publica" (agregado municipal)
# --------------------------------------------------------------------------------------
def carrega_ideb(arquivo, sheet, prefixo):
    bruto = pd.read_excel(f"{RAW}/{arquivo}", sheet_name=sheet, header=None, skiprows=10)
    header = pd.read_excel(f"{RAW}/{arquivo}", sheet_name=sheet, header=None, nrows=10).iloc[9]
    cols_obs = [i for i, v in enumerate(header) if isinstance(v, str) and v.startswith("VL_OBSERVADO_")]
    col_2025 = [i for i in cols_obs if header[i] == "VL_OBSERVADO_2025"][0]
    col_2023 = [i for i in cols_obs if header[i] == "VL_OBSERVADO_2023"][0]

    df = bruto[[1, 3, col_2023, col_2025]].copy()
    df.columns = ["cd_mun", "rede", "ideb_2023", "ideb_2025"]
    df = df[df["rede"] == "Pública"].copy()
    df["cd_mun"] = df["cd_mun"].astype("Int64").astype(str)

    for c in ("ideb_2023", "ideb_2025"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # usa 2025 quando disponivel; cai para 2023 quando o municipio ainda nao teve resultado publicado em 2025
    df[f"{prefixo}_ano_ref"] = df["ideb_2025"].notna().map({True: 2025, False: 2023})
    df[prefixo] = df["ideb_2025"].fillna(df["ideb_2023"])
    return df[["cd_mun", prefixo, f"{prefixo}_ano_ref"]]


ideb_ai = carrega_ideb("divulgacao_anos_iniciais_municipios_2025.xlsx", "IDEB_AI_MUNICÍPIOS", "ideb_anos_iniciais")
ideb_af = carrega_ideb("divulgacao_anos_finais_municipios_2025.xlsx", "IDEB_AF_MUNICÍPIOS", "ideb_anos_finais")
ideb_em = carrega_ideb("divulgacao_ensino_medio_municipios_2025.xlsx", "IDEB_Municípios (ENSINO MÉDIO)", "ideb_ensino_medio")

print(f"[ideb] anos iniciais: {len(ideb_ai)} municipios | anos finais: {len(ideb_af)} | ensino medio: {len(ideb_em)}")

# --------------------------------------------------------------------------------------
# 4. Merge final pelo cd_mun (codigo IBGE)
# --------------------------------------------------------------------------------------
base = ref[["cd_mun", "nm_mun", "sigla_uf", "cd_rgi", "cd_rgint", "area_km2", "cd_tse"]].copy()
base = base[base["cd_mun"] != "5101837"]  # Boa Esperanca do Norte: sem dados censitarios 2022 (ver PDF)

final = (
    base
    .merge(ips_sel, on="cd_mun", how="left")
    .merge(ideb_ai, on="cd_mun", how="left")
    .merge(ideb_af, on="cd_mun", how="left")
    .merge(ideb_em, on="cd_mun", how="left")
)

final = final.sort_values("cd_mun").reset_index(drop=True)
final.to_csv(f"{OUT}/grupo_seguranca_educacao.csv", index=False, encoding="utf-8-sig")

print(f"[final] tabela unificada: {final.shape[0]} municipios x {final.shape[1]} colunas")
print(f"[final] faltantes ips_geral: {final['ips_geral'].isna().sum()}")
print(f"[final] faltantes ideb_anos_iniciais: {final['ideb_anos_iniciais'].isna().sum()}")
print(f"[final] faltantes ideb_anos_finais: {final['ideb_anos_finais'].isna().sum()}")
print(f"[final] faltantes ideb_ensino_medio: {final['ideb_ensino_medio'].isna().sum()}")

# --------------------------------------------------------------------------------------
# 5. Estatisticas descritivas (para a secao de EDA do relatorio)
# --------------------------------------------------------------------------------------
vars_eda = [
    "populacao_2025", "pib_per_capita", "ips_geral", "ips_seguranca_pessoal",
    "ips_homicidios", "ips_assassinatos_jovens", "ips_assassinatos_mulheres",
    "ips_mortes_transito", "ips_violencia_mulheres", "ips_acesso_conhecimento_basico",
    "ips_abandono_fundamental", "ips_abandono_medio", "ips_evasao_medio",
    "ips_nota_mediana_enem", "ideb_anos_iniciais", "ideb_anos_finais", "ideb_ensino_medio",
]
desc = final[vars_eda].describe().T
desc["faltantes"] = final[vars_eda].isna().sum()
desc["pct_faltantes"] = (desc["faltantes"] / len(final) * 100).round(2)
desc = desc.rename(columns={
    "count": "n_validos", "mean": "media", "std": "desvio_padrao",
    "min": "minimo", "25%": "q1", "50%": "mediana", "75%": "q3", "max": "maximo",
})
desc = desc[["n_validos", "faltantes", "pct_faltantes", "media", "desvio_padrao", "minimo", "q1", "mediana", "q3", "maximo"]]
desc.round(3).to_csv(f"{OUT}/estatisticas_descritivas.csv", encoding="utf-8-sig")

print("\n[EDA] estatisticas descritivas:")
with pd.option_context("display.width", 200, "display.max_columns", 20):
    print(desc.round(2))

print("\nOK - arquivos gerados em 'Dados processados/'")
