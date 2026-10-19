# Parte 2: resultados completos para selecionar depois

Escopo: primeiro turno das eleições de 2026, presidente no Brasil e deputado federal em Minas Gerais. A mesma análise é aplicada a todos os candidatos que receberam votos e a todos os partidos do cadastro desses cargos. Não há seleção automática de casos para o relatório.

Execução completa: **13 candidatos presidenciais e 720 candidatos a deputado federal em MG**, após excluir 37 candidatos sem votos. Foram processados 13 partidos no escopo presidencial e 26 no escopo MG. Os resultados contêm 3.088 linhas de Moran global (incluindo os diagnósticos de amostra insuficiente na UF única de MG) e 6.176 combinações de entidade/indicador; 5.864 destas correspondem a candidatos e atendem ao item 6c. A execução utilizou 999 permutações e semente 2026.

## Executar

As referências já exportadas permitem executar localmente sem conexão ao servidor. Os três scripts encontram os arquivos a partir da localização do repositório, independentemente da pasta corrente.

```sh
uv venv --python python3 .venv
uv pip install --python .venv/bin/python -r requirements-parte2.txt
.venv/bin/python scripts/03_preparar_parte2.py
.venv/bin/python scripts/04_analisar_parte2.py
.venv/bin/python scripts/05_visualizar_parte2.py
```

Somente se for necessário obter novamente limites, vizinhos e dados censitários:

```sh
.venv/bin/python scripts/03_preparar_parte2.py --exportar-referencias
```

Esse comando utiliza uma transação PostgreSQL somente leitura. As variáveis `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` e `PGPASSWORD` podem substituir a conexão da disciplina. Nenhum script da Parte 2 cria ou substitui tabelas no servidor. Não é necessário executar `02_carga_postgis.py`.

## Arquivos para filtrar

Todos os resultados estão em `Dados processados/parte2/`. CSVs usam UTF-8 com BOM, separador vírgula e ponto decimal. Pandas lê diretamente os arquivos `.csv.gz`, sem extração prévia.

| Arquivo | Conteúdo |
|---|---|
| `catalogo_candidatos.csv` | Identificador, número, nome de urna, partido, situação no primeiro turno e total de votos do escopo de todos os candidatos com votos. |
| `candidatos_excluidos_sem_votos.csv` | Candidatos retirados por terem zero votos no escopo completo. |
| `catalogo_partidos.csv` | Números e siglas dos partidos por escopo. |
| `votacao_candidatos.csv.gz` | Grade completa candidato × território nos quatro níveis, com votos, denominador e percentual. |
| `votacao_partidos.csv.gz` | Mesmo formato, somando votos nominais e de legenda por partido. |
| `totais_votacao.csv` | Totais por categoria e denominador em cada território. |
| `indicadores_municipais.csv` | Parte 1 integrada à população e ao rendimento do Censo 2022. |
| `moran_global.csv` | I de Moran, p bilateral, q ajustado e diagnóstico por candidato/partido e nível. Inclui nomes e situação eleitoral para filtrar. |
| `comparacao_escalas.csv` | Os resultados municipal, imediato, intermediário e estadual na mesma linha por entidade. |
| `correlacoes.csv` | Pearson, Spearman e Moran bivariado municipais para cada candidato/partido e indicador, com p, q e cobertura. |
| `diagnostico_pesos.csv` | Quantidade de observações espaciais, ilhas excluídas e componentes conexos. |
| `perfis_municipais.csv` | Quatro perfis de segurança/educação, mais a categoria sem dados. |
| `votacao_por_perfil.csv` | Votos e percentuais agregados por perfil e candidato/partido. |
| `limiares_perfis.csv` | Medianas usadas no agrupamento de municípios. |
| `auditoria_preparacao.json` | Cobertura, exclusões e reconciliação dos totais. |
| `metodo_analise.json` | Semente, permutações, métodos e dimensão da execução. |
| `fontes_bdg.json` | Tabelas compartilhadas efetivamente exportadas e data de obtenção. |
| `referencias.gpkg` | Limites cartográficos dos quatro níveis, utilizáveis no QGIS. |
| `vizinhos.csv` | Contiguidade derivada das geometrias originais, antes da simplificação cartográfica. |

Os arquivos `*_parcial.csv` são checkpoints de execução e não devem ser usados no relatório: os CSVs finais contêm os ajustes de múltiplos testes e os metadados completos.

Exemplo de filtro, sem recalcular as estatísticas:

```python
import pandas as pd

resultados = pd.read_csv("Dados processados/parte2/moran_global.csv", dtype={"id_entidade": str})
municipais_mg = resultados[
    (resultados["escopo"] == "deputado_federal_MG")
    & (resultados["tipo"] == "candidato")
    & (resultados["nivel"] == "municipio")
    & (resultados["status"] == "ok")
]
municipais_mg.to_csv("selecao_mg.csv", index=False)
```

Para extrair os resultados e gerar mapas de qualquer caso, substitua o marcador por um código do catálogo:

```sh
.venv/bin/python scripts/05_visualizar_parte2.py --escopo presidente_BR --candidato CODIGO_SQ_OU_NUMERO
.venv/bin/python scripts/05_visualizar_parte2.py --escopo deputado_federal_MG --candidato CODIGO_SQ_OU_NUMERO
.venv/bin/python scripts/05_visualizar_parte2.py --escopo deputado_federal_MG --partido NUMERO_OU_SIGLA
```

As pastas individuais contêm um mapa com quatro painéis e CSVs já filtrados. Não é necessário reprocessar os ZIPs ou repetir as permutações.

## Correspondência com o enunciado

| Item | Resultados disponíveis | Trabalho editorial após escolher os casos |
|---|---|---|
| 6a | `moran_global.csv`, votos e catálogo com situação eleitoral | Selecionar candidatos nacionais e estaduais; discutir padrões amplos/regionalizados e eleitos/não eleitos. |
| 6b | `comparacao_escalas.csv` e mapas extraíveis | Explicar preservação ou mudança dos padrões nas regiões imediatas e intermediárias. |
| 6c | `correlacoes.csv` | Interpretar associação municipal e espacial com segurança, educação e variáveis censitárias. |
| 6d | Resultados com `tipo=partido`, somando nominal e legenda | Selecionar pequeno grupo de partidos representativos e compará-los. Para presidente, o partido é o do candidato, não a coligação inteira. |
| 6e | Perfis, limiares e votação por perfil | Discutir o agrupamento descritivo de municípios. |
| 7 | Figuras gerais e mapas individuais com método descrito abaixo | Incluir as visualizações pertinentes e explicar suas escolhas. |
| 8 | Resultados, métodos e identificação das fontes | Expandir o relatório da Parte 1, incorporar a discussão dos casos escolhidos e preparar os slides. |

Esta execução completa dá suporte à seleção posterior. Ela não substitui o relatório interpretativo nem os slides exigidos na entrega.

## Métodos e decisões

- **Votação:** soma das seções por município e depois por região imediata, região intermediária e UF. Percentuais regionais são calculados após somar numerador e denominador; não são médias de percentuais municipais.
- **Denominador:** votos nominais mais votos de legenda registrados no arquivo; exclui códigos de branco (95), nulo (96) e anulado/apurado em separado (97). Não é uma certificação jurídica de votos válidos: o arquivo de votação por seção não discrimina completamente a destinação jurídica dos votos nominais. A denominação das colunas e figuras mantém essa definição explícita.
- **Candidatos sem votos:** excluídos apenas quando o total do escopo é zero. No caso presidencial, a verificação inclui o exterior. Municípios cobertos onde um candidato ativo recebeu zero votos continuam na amostra.
- **Exterior:** preservado em arquivo separado, sem atribuição artificial a municípios brasileiros e sem participação nos testes espaciais domésticos.
- **Contiguidade:** Queen por `ST_Touches` nas geometrias originais das tabelas compartilhadas; pesos padronizados por linha. Cada nível tem sua própria vizinhança. Em MG, a matriz é restrita ao estado.
- **Ilhas:** não recebem conexões artificiais. São retiradas somente dos testes espaciais; permanecem nas votações e correlações comuns. A lista e a amostra efetiva são registradas. Não há autocorrelação estadual calculável para deputado federal de MG, pois existe apenas uma UF nesse escopo; a agregação estadual é preservada.
- **Estatísticas:** Moran global dos percentuais eleitorais; Pearson e Spearman municipais; Moran bivariado com percentual eleitoral em `x` e indicador complementar em `y`. O bivariado associa o voto local ao indicador dos vizinhos, e não é simétrico entre `x` e `y`. As implementações seguem [esda.Moran](https://pysal.org/esda/stable/generated/esda.Moran.html) e [esda.Moran_BV](https://pysal.org/esda/stable/generated/esda.Moran_BV.html).
- **Inferência:** 999 permutações, semente 2026 e p bilateral explícito. `q_fdr_bh` ajusta múltiplos testes por Benjamini–Hochberg, separadamente por escopo/tipo/nível no Moran global e por escopo/tipo/indicador nas correlações. Os p de Pearson/Spearman são convencionais e não corrigem dependência espacial; o teste espacial é apresentado separadamente. Não selecionar resultados somente pelo p bruto.
- **Indicadores:** homicídios, ENEM, três etapas do IDEB, PIB per capita, rendimento médio censitário e densidade demográfica censitária. Faltantes são excluídos por indicador; a matriz espacial é reconstruída na amostra efetiva. Não há imputação de IDEB nem transformação de ausência em zero.
- **Boa Esperança do Norte:** permanece na votação e nas agregações territoriais. Ausências de Censo 2022 e dos indicadores da Parte 1 são preservadas. Os dois polígonos de lagoas são excluídos.
- **Análise extra:** quatro perfis definidos pelo cruzamento de homicídios e ENEM acima/abaixo das medianas. Limiares são calculados separadamente para Brasil e MG; igualdade entra em acima. É um agrupamento descritivo, sem modelo de clustering. As participações por perfil usam a soma dos votos e denominadores, não a média de percentuais municipais.
- **Limites:** municípios do Censo 2022 e malha 2025 podem ter diferenças territoriais. Os indicadores têm anos de referência distintos. Associação municipal não demonstra causalidade nem comportamento individual dos eleitores.

## Visualizações: item 7

**Propósito:** localizar padrões geográficos, comparar escalas para o mesmo caso e mostrar a distribuição dos resultados completos. Os perfis visualizam a análise extra.

**Plano de fundo:** polígonos oficiais do BDG/IBGE sobre fundo branco, sem mapa de ruas, que não ajuda à comparação municipal nessa escala. Dados ausentes são cinza.

**Parâmetros:** projeção SIRGAS 2000 / Brazil Polyconic (EPSG:5880); paleta sequencial para percentuais; mesma escala de cores nos quatro níveis de cada caso; cores categóricas para os perfis. A tolerância de simplificação de 0,001 grau serve somente para desenho. As estatísticas usam os vizinhos das geometrias originais.

**Produção:** Python, GeoPandas e Matplotlib; PNG a 180 dpi. Figuras ficam em `Relatorio/figuras_parte2/`. As versões utilizadas estão em `requirements-parte2.txt`.

## Tabelas do BDG utilizadas: item 8

Limites e chaves: `geodata.munic`, `geodata.micro`, `geodata.meso`, `geodata.estado`.

Censo: `geodata.sexo_fx_etaria_simplif` (população) e `geodata.renda_trabalho` (rendimentos). A população 2025 e o PIB per capita da Parte 1 continuam identificados como provenientes do IPS; não foram renomeados como Censo.

Tema complementar: arquivo local `grupo_seguranca_educacao.csv`, já carregado na Parte 1 em `geodata.thaylor_verteiro_seguranca_educacao`. A Parte 2 reutiliza o CSV entregue; não depende de alterações posteriores nessa tabela compartilhada.

Estruturas auxiliares novas: os CSVs e o GeoPackage locais listados acima. Não foram criadas tabelas auxiliares no servidor.

## Extra adicional: ENEM e orientação do partido mais votado

O agrupamento por homicídios e ENEM foi preservado. Uma segunda análise extra compara a nota mediana municipal do ENEM entre grupos definidos pelo partido mais votado, para presidente no Brasil e deputado federal em MG.

```sh
.venv/bin/python scripts/06_enem_ideologia.py
```

Esse comando usa os dados já preparados e não repete os testes das análises anteriores. Os resultados, a classificação de referência, as exclusões e as figuras estão descritos em [ENEM_e_ideologia.md](ENEM_e_ideologia.md). Os arquivos novos começam com `enem_ideologia_` em `Dados processados/parte2/` e `Relatorio/figuras_parte2/`.
