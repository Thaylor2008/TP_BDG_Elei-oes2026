# TP_BDG_Eleicoes2026
Análise Espacial de Dados de Segurança Pública (IPS Brasil) e Educação (IDEB) integrada ao Censo IBGE 2022 — Trabalho Prático Parte 1 (BDG/UFMG).
# 📊 Trabalho Prático — Parte 1: Engenharia de Dados e Análise Exploratória
**Disciplina:** Bancos de Dados Geográficos e Ciência de Dados Geoespaciais (ICEx - UFMG)  
**Projeto:** Análise Espacial dos Dados Eleitorais de 2026

---

## 🎯 Objetivo
Este repositório contém a base de dados, scripts de engenharia de dados e o modelo do relatório em LaTeX da **Parte 1** do trabalho. O foco do grupo é analisar a relação entre **Indicadores de Segurança Pública (IPS Brasil)** e **Desempenho Educacional (IDEB/INEP)** em escala municipal no Brasil, integrando-os às malhas territoriais e variáveis socioeconômicas do **Censo IBGE 2022**.

---

## 📁 Estrutura dos Arquivos do Repositório

* **`/dados_brutos/`**:
  * `IPS Brasil - Tabela de Dados.csv` — Indicadores de Segurança Pessoal, Homicídios e IPS Municipal.
  * `divulgacao_anos_iniciais_municipios_2025/` — Notas do IDEB (Anos Iniciais do Ensino Fundamental).
  * `divulgacao_anos_finais_municipios_2025/` — Notas do IDEB (Anos Finais do Ensino Fundamental).
  * `divulgacao_ensino_medio_municipios_2025/`— Notas do IDEB (Ensino Medio).
* **`/relatorio/`**:
  * `relatorio_parte1_template.tex` — Estrutura completa em LaTeX/ABNT para o Overleaf.

---

## 🛠️ Próximos Passos (Grupo)
1. **Tratamento de Dados:** Selecionar variáveis de interesse no Python/Excel mantendo o código IBGE do município (`cd_mun`).
2. **Carga no PostGIS:** Subir a tabela unificada para o servidor no schema `geodata` (`grupox_seguranca_educacao`).
3. **Relatório:** Preencher as seções no Overleaf com a justificativa do tema e resultados da Análise Exploratória (EDA).
