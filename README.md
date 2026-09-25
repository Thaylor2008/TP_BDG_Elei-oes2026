# TP_BDG_Eleicoes2026 🗳️🗺️

**Análise Espacial de Dados de Segurança Pública (IPS Brasil) e Educação (IDEB/ENEM) integrada ao Censo IBGE 2022**  
*Trabalho Prático da disciplina de Bancos de Dados Geográficos e Ciência de Dados Geoespaciais (BDG)*  
**Departamento de Ciência da Computação (DCC) — ICEx / UFMG**  
**Professor:** Clodoveu Davis | **Semestre:** 2026/2

---

## 📌 Status do Projeto
- [x] **Parte 1: Engenharia de Dados e Análise Exploratória (EDA)** — **CONCLUÍDA E ENTREGUE** ✅
- [ ] **Parte 2: Análise Espacial, Autocorrelação (I de Moran) e Dados Eleitorais 2026** — *Aguardando dados oficiais do TSE pós-primeiro turno* ⏳

---

## 🎯 Visão Geral e Objetivo

Este repositório contém o código, as rotinas de tratamento de dados (ETL), os artefatos cartográficos e o relatório técnico da **Parte 1** do Trabalho Prático da disciplina de BDG/UFMG.

O objetivo do projeto é investigar a relação espacial e socioeconômica entre os eixos de **Segurança Pública** (mensurada via Índice de Progresso Social - IPS Brasil 2026) e **Desempenho Educacional** (IDEB/INEP e Nota Mediana do ENEM) em nível municipal para os 5.570 municípios do Brasil, integrados às malhas digitais e variáveis do **Censo IBGE 2022**.

---

## 👥 Equipe
* **Thaylor Weslei Dias G. Verteiro**
* **Bruno Soares e Silva**
* **Bernardo Alves Miranda**
* **Camila Nicola Dias Santana**
* **Igor Novais Barroso** 
* **Lucas Albuquerque Santos Costa** 
---

## 📁 Estrutura do Repositório

TP_BDG_Eleicoes2026/ ├── scripts/ │   ├── etl_limpeza_organizacao.py       # Pipeline Python para normalização, pareamento em 3 passadas e junção IPS + IDEB │   └── upload_postgis.py               # Script de DDL e carga dos dados no PostgreSQL/PostGIS (Servidor UFMG) ├── dados/ │   ├── estatisticas_descritivas.csv     # Tabela com o resumo estatístico completo das variáveis │   └── grupo_seguranca_educacao.csv    # Base unificada com os 5.570 municípios e 34 atributos tratados ├── mapas/ │   ├── Mapa - Homicídios.png            # Mapa temático da Taxa de Homicídios por município │   └── Mapa - Mediana ENEM.png          # Mapa temático da Nota Mediana do ENEM no Brasil ├── relatorio/ │   ├── Relatorio_Parte1.pdf             # PDF final do relatório submetido no Moodle │   └── relatorio_parte1_template.tex    # Código-fonte do relatório completo em LaTeX/ABNT └── README.md                            # Documentação principal do repositório

---

## 🛠️ Engenharia de Dados & Carga no Banco (PostGIS)

### 1. Pareamento de Chaves Espaciais (ETL em Python)
Como a base do **IPS Brasil** não possuía o Código IBGE (`cd_mun`), desenvolveu-se um algoritmo de pareamento em **3 passadas**:
1. **Normalização Estrita:** Remoção de acentos/ASCII, pontuação e conversão para caixa alta (`NOME/UF`).
2. **Normalização Semântica (*Loose Match*):** Remoção de preposições (`DE`, `DO`, `DA`, `DOS`, `DAS`, `D'`).
3. **Dicionário de Exceções Manuais:** Mapeamento direto de divergências ortográficas específicas (ex: *Graccho Cardoso/SE*, *Arez/RN*, *Assu/RN*, *São Luiz do Anauá/RR*).
* **Resultado:** **100% dos 5.570 municípios pareados com sucesso**.

### 2. Carga no Servidor PostgreSQL/PostGIS
A base foi importada e disponibilizada no banco de dados espacial da disciplina:
* **Servidor:** `150.164.2.42:5432` | **Banco:** `bdg2026`
* **Schema / Tabela:** `geodata.thaylor_verteiro_seguranca_educacao`
* **Chave Primária:** `cd_mun` (Código IBGE de 7 dígitos), associada à camada espacial `geodata.munic.geom`.

---

## 📊 Resultados da Análise Exploratória (EDA)

| Indicador | Média | Mediana | Desv. Padrão | Mínimo | Máximo | Faltantes (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **População (2025)** | 38.315,11 | 11.358,50 | 217.438,60 | 856,00 | 11.904.961,00 | 0,00% |
| **PIB per capita (R\$)** | R\$ 39.026,01 | R\$ 29.107,21 | R\$ 38.854,28 | R\$ 6.771,94 | R\$ 678.813,83 | 0,00% |
| **IPS Geral** | 60,44 | 60,53 | 4,38 | 42,44 | 73,10 | 0,00% |
| **Taxa de Homicídios** | 17,50 | 13,14 | 16,03 | 0,00 | 220,27 | 0,00% |
| **Violência c/ Mulheres** | 200,16 | 127,28 | 230,89 | 0,00 | 2.525,71 | 0,00% |
| **Evasão Ensino Médio (%)** | 8,72% | 8,30% | 3,23% | 1,27% | 24,46% | 0,00% |
| **Nota Mediana ENEM** | 511,41 | 508,93 | 34,25 | 405,95 | 652,96 | 0,00% |
| **IDEB Anos Iniciais** | 6,22 | 6,20 | 0,87 | 3,30 | 10,00 | 0,95% |
| **IDEB Anos Finais** | 5,11 | 5,10 | 0,74 | 2,80 | 9,30 | 0,48% |
| **IDEB Ensino Médio** | 4,47 | 4,50 | 0,58 | 2,40 | 7,20 | 0,93% |

---

## 🚀 Próximos Passos (Parte 2)

Com a Parte 1 finalizada, os próximos passos do projeto englobam:
1. **Dados Eleitorais 2026:** Ingestão das estatísticas oficiais de votação disponibilizadas pelo TSE pós-primeiro turno.
2. **Autocorrelação Espacial:** Aplicação dos testes de **I de Moran Global** e **I de Moran Local (LISA)** para identificar *clusters* espaciais (Alto-Alto, Baixo-Baixo).
3. **Re-agregação Territorial:** Análise dos indicadores nos níveis de Regiões Geográficas Imediatas (RGI), Intermediárias (RGINT) e Unidades da Federação (UF).
4. **Relatório Final:** Discussão da correlação entre voto e os indicadores de Segurança Pública e Educação.

---

## 🔗 Links e Recursos
* 📄 **Relatório no Overleaf:** [Projeto no Overleaf](https://www.overleaf.com/project/6ab1a889055363a01b36ddc1/share#8ecf51ca0faa686010278c76ab4c6025a818ef164292c65f)
* 🎓 **Disciplina:** Bancos de Dados Geográficos (DCC/ICEx/UFMG)
