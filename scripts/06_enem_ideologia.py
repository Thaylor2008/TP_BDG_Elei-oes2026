"""Extra adicional: ENEM municipal por orientacao do partido mais votado.

Presidente/BR: partido do candidato mais votado no municipio, no primeiro turno.
Deputado federal/MG: partido com mais votos nominais + legenda no municipio.
Classificacao historica publicada: Bolognesi et al. (2025), Tabela 1, referencia 2022.
Comparacao descritiva: nao atribui causalidade nem calcula p-valores sem controle espacial.
Uso: .venv/bin/python scripts/06_enem_ideologia.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Dados processados/parte2"
REF = ROOT / "Dados brutos/ref/classificacao_ideologica_partidos.csv"
FIG = ROOT / "Relatorio/figuras_parte2"
SOURCE = "https://doi.org/10.1590/1807-0191202531120"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SCOPES = {"presidente_BR": "Presidente no Brasil", "deputado_federal_MG": "Deputado federal em MG"}
GROUPS = ["Esquerda", "Centro", "Direita"]
COLORS = {"Esquerda": "#756bb1", "Centro": "#66a61e", "Direita": "#e6550d",
          "Sem classificação": "#bdbdbd", "Empate": "#333333"}


def read(name):
    return pd.read_csv(DATA / name, dtype={"codigo_geo": str, "cd_mun": str,
                                          "sq_candidato": str, "nr_partido": str})


def save(frame, name):
    frame.to_csv(DATA / name, index=False, encoding="utf-8-sig", float_format="%.10g")


def municipal_leaders(votes, catalog, scope, key):
    """Preserva empates explicitamente, sem escolher pelo numero ou pela ordem."""
    block = votes[(votes.escopo == scope) & (votes.nivel == "municipio")].copy()
    if block.empty or block.duplicated(["codigo_geo", key]).any():
        raise ValueError(f"Votacao vazia ou duplicada: {scope}")
    maximum = block.groupby("codigo_geo").votos.transform("max")
    top = block[block.votos == maximum].merge(
        catalog[catalog.escopo == scope], on=["escopo", key], how="left", validate="many_to_one")
    if top.sg_partido.isna().any() or (top.votos <= 0).any():
        raise ValueError("Lider sem cadastro ou sem votos")
    leaders = top.groupby("codigo_geo", sort=True).agg(
        n_lideres=(key, "size"), votos_lider=("votos", "first"), percentual_lider=("percentual", "first"),
        sg_partido_mais_votado=("sg_partido", lambda s: s.iloc[0] if len(s) == 1 else ""),
        partidos_no_topo=("sg_partido", lambda s: ";".join(sorted(set(s)))),
    ).reset_index().rename(columns={"codigo_geo": "cd_mun"})
    leaders["escopo"] = scope
    return leaders


def run():
    classification = pd.read_csv(REF)
    if classification.sg_partido.duplicated().any() or not classification.grupo.isin(GROUPS).all():
        raise ValueError("Classificacao ambigua ou categoria invalida")
    indicators = read("indicadores_municipais.csv")
    candidate_votes, party_votes = read("votacao_candidatos.csv.gz"), read("votacao_partidos.csv.gz")
    candidates, parties = read("catalogo_candidatos.csv"), read("catalogo_partidos.csv")
    all_municipalities, summaries, comparisons = [], [], []
    audit = {"fonte_classificacao": SOURCE, "referencia_classificacao": 2022,
             "unidade": "municipio; mesmo peso para cada municipio",
             "comparacao": "descritiva; sem teste de significancia",
             "agrupamento": "centro-esquerda e categorias a esquerda -> Esquerda; centro-direita e categorias a direita -> Direita; centro -> Centro",
             "escopos": {}}
    for scope in SCOPES:
        if scope == "presidente_BR":
            leaders = municipal_leaders(candidate_votes, candidates, scope, "sq_candidato")
        else:
            leaders = municipal_leaders(party_votes, parties, scope, "nr_partido")
        expected = indicators if scope == "presidente_BR" else indicators[indicators.sigla_uf == "MG"]
        if set(leaders.cd_mun) != set(expected.cd_mun):
            raise ValueError(f"Cobertura municipal incompleta: {scope}")
        frame = leaders.merge(
            indicators[["cd_mun", "nm_mun", "sigla_uf", "ips_nota_mediana_enem"]],
            on="cd_mun", how="left", validate="one_to_one")
        frame = frame.merge(classification, left_on="sg_partido_mais_votado", right_on="sg_partido",
                            how="left", validate="many_to_one").drop(columns="sg_partido")
        frame["grupo"] = frame.grupo.fillna("Sem classificação")
        frame.loc[frame.n_lideres > 1, "grupo"] = "Empate"
        frame["incluido_comparacao"] = frame.grupo.isin(GROUPS) & frame.ips_nota_mediana_enem.notna()
        all_municipalities.append(frame)
        summary = frame.groupby("grupo", sort=False).agg(
            municipios=("cd_mun", "size"), municipios_com_enem=("ips_nota_mediana_enem", "count"),
            media_enem=("ips_nota_mediana_enem", "mean"), mediana_enem=("ips_nota_mediana_enem", "median"),
            q1_enem=("ips_nota_mediana_enem", lambda s: s.quantile(.25)),
            q3_enem=("ips_nota_mediana_enem", lambda s: s.quantile(.75)),
        ).reset_index().assign(escopo=scope)
        summaries.append(summary)
        left = frame.loc[(frame.grupo == "Esquerda") & frame.incluido_comparacao, "ips_nota_mediana_enem"]
        right = frame.loc[(frame.grupo == "Direita") & frame.incluido_comparacao, "ips_nota_mediana_enem"]
        comparisons.append({"escopo": scope, "n_esquerda": len(left), "n_direita": len(right),
                            "mediana_esquerda": left.median(), "mediana_direita": right.median(),
                            "diferenca_direita_menos_esquerda": right.median() - left.median(),
                            "tipo_comparacao": "descritiva; sem inferencia causal ou teste de significancia"})
        unknown = frame.loc[frame.grupo == "Sem classificação", "sg_partido_mais_votado"].value_counts().to_dict()
        audit["escopos"][scope] = {"municipios": len(frame), "empates": int((frame.grupo == "Empate").sum()),
                                    "sem_enem": int(frame.ips_nota_mediana_enem.isna().sum()),
                                    "sem_classificacao_por_partido": unknown,
                                    "municipios_comparados": int(frame.incluido_comparacao.sum()),
                                    "grupos": frame.grupo.value_counts().to_dict()}
        plot(frame, scope)
    save(pd.concat(all_municipalities, ignore_index=True), "enem_ideologia_municipios.csv")
    save(pd.concat(summaries, ignore_index=True), "enem_ideologia_resumo.csv")
    comparison = pd.DataFrame(comparisons)
    save(comparison, "enem_ideologia_comparacao.csv")
    (DATA / "enem_ideologia_metodo.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    write_report(comparison, audit)
    print("[OK] extra adicional gerado para ambos os escopos; analises anteriores preservadas", flush=True)


def plot(frame, scope):
    FIG.mkdir(parents=True, exist_ok=True)
    geo = gpd.read_file(DATA / "referencias.gpkg", layer="municipio")
    if scope == "deputado_federal_MG":
        geo = geo[geo.sigla_uf == "MG"]
    geo = geo.to_crs(5880).merge(frame[["cd_mun", "grupo"]], on="cd_mun", validate="one_to_one")
    fig, (map_ax, box_ax) = plt.subplots(1, 2, figsize=(14, 8), layout="constrained")
    for group in [*GROUPS, "Sem classificação", "Empate"]:
        part = geo[geo.grupo == group]
        if len(part):
            part.plot(ax=map_ax, color=COLORS[group], linewidth=0)
            map_ax.scatter([], [], color=COLORS[group], marker="s", label=f"{group} (n={len(part)})")
    map_ax.legend(loc="lower left", fontsize=8)
    map_ax.set_axis_off()
    map_ax.set_title("Orientação de referência do partido mais votado")
    groups = [group for group in GROUPS if ((frame.grupo == group) & frame.incluido_comparacao).any()]
    samples = [frame.loc[(frame.grupo == group) & frame.incluido_comparacao, "ips_nota_mediana_enem"] for group in groups]
    if samples:
        boxes = box_ax.boxplot(samples, tick_labels=[f"{group}\n(n={len(sample)})" for group, sample in zip(groups, samples)],
                               patch_artist=True, flierprops={"markersize": 2, "alpha": .3})
        for box, group in zip(boxes["boxes"], groups):
            box.set_facecolor(COLORS[group])
            box.set_alpha(.7)
    box_ax.set_ylabel("Nota mediana municipal do ENEM (Parte 1)")
    box_ax.set_title("Distribuição das notas por grupo")
    box_ax.grid(axis="y", alpha=.2)
    fig.suptitle(f"ENEM e orientação do partido mais votado | {SCOPES[scope]}")
    fig.supxlabel("TSE 2026, 1º turno; ENEM da Parte 1; referência ideológica de 2022. Cada município tem o mesmo peso. EPSG:5880.", fontsize=9)
    fig.savefig(FIG / f"enem_ideologia_{scope}.png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_report(comparison, audit):
    lines = ["# Análise extra adicional: ENEM e orientação do partido mais votado", "",
             "**Pergunta:** a nota mediana municipal do ENEM difere entre municípios onde o partido mais votado é classificado à esquerda ou à direita?", "",
             "Esta análise foi acrescentada; o agrupamento anterior por homicídios e ENEM continua disponível.", "",
             "## Como foi feita", "",
             "- Presidente no Brasil: partido do candidato mais votado em cada município, no primeiro turno.",
             "- Deputado federal em MG: partido com mais votos nominais e de legenda somados em cada município. Isso não significa que o partido conquistou uma cadeira nesse município.",
             "- A nota vem de `ips_nota_mediana_enem`, da Parte 1, ligada pelo código IBGE.",
             "- Cada município tem o mesmo peso. Comparamos as distribuições e a mediana das notas medianas municipais; não é a mediana de todos os estudantes desses municípios.",
             "- Empates, partidos sem classificação e notas ausentes ficam identificados e fora da comparação entre grupos.", "",
             "## Resultados", "",
             "| Escopo | Municípios de esquerda com ENEM | Municípios de direita com ENEM | Mediana do grupo de esquerda | Mediana do grupo de direita | Diferença: direita − esquerda |",
             "|---|---:|---:|---:|---:|---:|" ]
    for row in comparison.itertuples(index=False):
        lines.append(f"| {SCOPES[row.escopo]} | {row.n_esquerda} | {row.n_direita} | {row.mediana_esquerda:.2f} | {row.mediana_direita:.2f} | {row.diferenca_direita_menos_esquerda:+.2f} |")
    lines += ["", "As diferenças são descritivas. Não foi aplicado teste de significância nem controle por renda, região ou dependência espacial. Não demonstram efeito da ideologia sobre o desempenho educacional.", "",
              "## Cobertura", ""]
    for scope, item in audit["escopos"].items():
        lines.append(f"- **{SCOPES[scope]}:** {item['municipios']} municípios; {item['empates']} empates; {item['sem_enem']} sem ENEM; {item['municipios_comparados']} incluídos na comparação.")
        if item["sem_classificacao_por_partido"]:
            lines.append("  Partidos líderes sem classificação: " + "; ".join(f"{party}: {n} municípios" for party, n in item["sem_classificacao_por_partido"].items()) + ".")
    lines += ["", "## Classificação utilizada", "",
              f"Referência: [Bolognesi et al. (2025), Tabela 1]({SOURCE}), avaliação de especialistas de 2022. É uma referência histórica aplicada de forma exploratória aos dados de 2026, não uma medição da ideologia em 2026.", "",
              "Agrupamos centro-esquerda e categorias à esquerda como **Esquerda**; centro-direita e categorias à direita como **Direita**. Centro é mantido quando presente. Não inferimos categorias para partidos ausentes da fonte. O arquivo de referência registra a categoria original e a sigla usada na publicação.", "",
              "## Arquivos", "",
              "- [Classificação de referência](../Dados%20brutos/ref/classificacao_ideologica_partidos.csv).",
              "- [Municípios, partido líder, grupo e ENEM](../Dados%20processados/parte2/enem_ideologia_municipios.csv).",
              "- [Resumo dos grupos](../Dados%20processados/parte2/enem_ideologia_resumo.csv).",
              "- [Comparação esquerda/direita](../Dados%20processados/parte2/enem_ideologia_comparacao.csv).",
              "- Método e exclusões: `Dados processados/parte2/enem_ideologia_metodo.json`.", "",
              "## Figuras", "",
              "Os mapas mostram os grupos sobre limites IBGE/BDG, sem mapa de ruas. As caixas mostram a mediana e os quartis das notas, com pontos para valores além dos bigodes. Cores distinguem grupos, sem indicar desempenho melhor ou pior. Software: GeoPandas e Matplotlib; projeção EPSG:5880; PNG a 180 dpi.", "",
              "![Presidente no Brasil](figuras_parte2/enem_ideologia_presidente_BR.png)", "",
              "![Deputado federal em MG](figuras_parte2/enem_ideologia_deputado_federal_MG.png)", ""]
    (ROOT / "Relatorio/ENEM_e_ideologia.md").write_text("\n".join(lines))


if __name__ == "__main__":
    run()
