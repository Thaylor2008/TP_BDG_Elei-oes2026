# Hipóteses exploradas e resultados

Foram analisados **13 candidatos à Presidência no Brasil e 720 candidatos a deputado federal em MG**, no primeiro turno de 2026, além de seus partidos. Foram excluídos 37 candidatos sem votos.

As perguntas são exploratórias. **“Evidência estatística”** significa que o resultado passou pelo critério `q < 0,05`, ajustado para a realização de muitos testes. Foram utilizadas 999 permutações nos testes espaciais.

## 1. Municípios vizinhos apresentam votações parecidas?

**Hipótese:** a votação tem uma organização espacial, com resultados relacionados entre municípios vizinhos.

**Resultado:** houve evidência de dependência espacial para **13 dos 13 candidatos presidenciais** e **568 dos 720 candidatos a deputado federal em MG**. Entre os deputados, 567 apresentaram autocorrelação positiva e um apresentou autocorrelação negativa.

**O que significa:** para muitos candidatos, municípios próximos tendem a apresentar percentuais de votação semelhantes.

Em MG, houve evidência para **todos os 53 eleitos** e para **515 dos 667 demais candidatos**, incluindo suplentes. A comparação entre esses grupos foi descritiva, sem um teste específico de diferença entre eles.

## 2. O padrão permanece quando juntamos municípios em regiões maiores?

**Hipótese:** o padrão observado nos municípios pode mudar quando agregamos a votação.

**Resultado:** o número de candidatos com evidência de dependência espacial mudou conforme o nível analisado:

| Escopo | Municípios | Regiões imediatas | Regiões intermediárias |
|---|---:|---:|---:|
| Presidente no Brasil | 13 de 13 | 13 de 13 | 12 de 13 |
| Deputado federal em MG | 568 de 720 | 258 de 720 | 0 de 720 |

**O que significa:** a escala faz diferença. A evidência permaneceu para a maioria dos presidenciáveis e diminuiu nas regiões maiores de MG. Isso não prova ausência de padrão: a agregação também reduz o número de unidades disponíveis para o teste.

## 3. A votação está associada aos indicadores da Parte 1? Essa associação é espacial?

**Hipótese:** os percentuais de votação estão associados às características municipais levantadas na Parte 1.

Foram utilizados diretamente os valores de `grupo_seguranca_educacao.csv`, ligados à votação pelo código IBGE. **Foram analisados seis indicadores desse arquivo, não todas as suas colunas.**

**Resultado:** a tabela mostra quantos dos 733 candidatos apresentaram evidência de associação em cada teste:

| Indicador da Parte 1 | Pearson | Spearman | Moran bivariado |
|---|---:|---:|---:|
| Homicídios | 54 | 527 | 147 |
| Nota mediana do ENEM | 131 | 650 | 203 |
| IDEB — anos iniciais | 35 | 69 | 98 |
| IDEB — anos finais | 31 | 69 | 93 |
| IDEB — ensino médio | 32 | 126 | 112 |
| PIB per capita | 83 | 587 | 186 |

**Como ler:** Pearson verifica relações lineares; Spearman verifica se os valores aumentam ou diminuem juntos, sem exigir linearidade. O Moran bivariado verifica a associação da votação local com o indicador dos vizinhos. Os testes podem produzir resultados diferentes.

Os testes foram separados por escopo; a tabela apenas reúne as contagens. Um candidato pode aparecer em várias linhas.

**O que significa:** existem associações com a Parte 1, algumas com componente espacial. A direção varia por candidato; não há uma relação única para todos. Significância não significa necessariamente uma associação forte.

Adicionalmente, rendimento médio e densidade populacional do Censo 2022 apresentaram evidência de associação espacial para 328 e 124 candidatos, respectivamente.

## 4. A votação dos partidos também apresenta organização espacial?

**Hipótese:** somando a votação por partido, também encontramos semelhança entre municípios vizinhos.

**Resultado municipal:** houve autocorrelação positiva com evidência estatística para **13 dos 13 partidos presidenciais** e **25 dos 26 partidos com candidaturas a deputado federal em MG**.

Em MG, a evidência permaneceu para oito partidos nas regiões imediatas e para nenhum nas regiões intermediárias. Na Presidência, permaneceu para 13 e 12 partidos, respectivamente.

**O que significa:** a organização espacial também aparece nos partidos e depende da escala. Na Presidência, cada partido com votos corresponde a um candidato nesta base: não é uma confirmação independente. Para deputado federal, foram somados votos nominais e de legenda.

## 5. Municípios com perfis diferentes de segurança e educação apresentam votações diferentes?

**Hipótese exploratória extra:** agrupar municípios por homicídios e ENEM pode ajudar a descrever diferenças de votação.

Foram criados quatro perfis, combinando homicídios e ENEM acima/abaixo da mediana. Os limites foram calculados separadamente para Brasil e MG; igualdade entrou no grupo “acima”.

**Resultado:** todos os candidatos apresentaram alguma diferença de percentual entre os perfis. Foram classificados 5.570 municípios no Brasil e todos os 853 de MG. Um município brasileiro ficou sem perfil por falta de indicadores.

**Limite:** a comparação é descritiva; não foi testada a significância das diferenças entre perfis.

## 6. Extra adicional: o ENEM difere conforme a orientação do partido mais votado?

**Hipótese exploratória:** municípios onde o partido mais votado é classificado à esquerda ou à direita podem apresentar notas medianas do ENEM diferentes. Esta análise foi acrescentada, preservando a análise dos quatro perfis da seção anterior.

Na Presidência, usamos o partido do candidato mais votado no município. Para deputado federal em MG, somamos os votos nominais e de legenda de cada partido. “Mais votado” aqui não significa conquistar uma cadeira no município.

**Resultado:** comparando a mediana das notas medianas municipais:

| Escopo | Grupo de esquerda | Grupo de direita | Diferença: direita − esquerda |
|---|---:|---:|---:|
| Presidente no Brasil | 494,78 | 523,94 | +29,16 pontos |
| Deputado federal em MG | 511,13 | 525,62 | +14,49 pontos |

Cada município tem o mesmo peso. No caso presidencial, foram comparados 2.663 municípios do grupo de esquerda e 2.905 do grupo de direita; dois empates e uma nota ausente ficaram fora. Em MG, foram comparados 100 e 735 municípios, respectivamente; 18 municípios liderados pelo PRD ficaram sem classificação na fonte adotada.

**O que significa:** nesta comparação descritiva, o grupo de direita apresentou mediana maior nos dois escopos. Isso não demonstra efeito da ideologia sobre as notas. Não foram aplicados teste de significância nem controles por região, renda ou dependência espacial.

A orientação é uma referência histórica de especialistas de 2022, aplicada de forma exploratória a 2026, e não uma avaliação atual dos partidos. Fonte, critérios e mapas: [ENEM e ideologia](ENEM_e_ideologia.md).

## Cuidados ao interpretar

- As associações não demonstram que segurança, educação ou renda causaram determinado resultado eleitoral.
- Os dados são municipais: não permitem concluir como cada pessoa votou.
- Os indicadores têm anos de referência diferentes. Dados ausentes foram preservados, sem substituição por zero.

## Onde conferir os resultados

- [Autocorrelação dos candidatos e partidos](../Dados%20processados/parte2/moran_global.csv).
- [Correlações com os indicadores, incluindo sinal e intensidade](../Dados%20processados/parte2/correlacoes.csv).
- [Comparação entre escalas](../Dados%20processados/parte2/comparacao_escalas.csv).
- [Votação por perfil municipal](../Dados%20processados/parte2/votacao_por_perfil.csv).
- [Instruções para filtrar casos e gerar mapas](Parte2_Como_usar.md).

Os resultados calculados dão suporte à escolha dos casos que entrarão no relatório final e nos slides exigidos pelo trabalho.
