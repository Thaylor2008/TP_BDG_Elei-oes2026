"""Figuras gerais e extracao de qualquer candidato/partido, depois da analise completa.

Sem argumentos: mapas tematicos/perfis e distribuicao dos resultados globais.
Selecao: --escopo presidente_BR --candidato NUMERO_OU_SQ
         --escopo deputado_federal_MG --partido NUMERO_OU_SIGLA
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1] / ".cache"))
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Dados processados/parte2"
FIG = ROOT / "Relatorio/figuras_parte2"
LEVELS = {"municipio": ("cd_mun", "Municipios"), "rgi": ("cd_rgi", "Regioes imediatas"),
          "rgint": ("cd_rgint", "Regioes intermediarias"), "uf": ("sigla_uf", "Estados")}


def read(name):
    return pd.read_csv(DATA / name, dtype={"codigo_geo": str, "cd_mun": str,
                                          "sq_candidato": str, "nr_candidato": str,
                                          "nr_partido": str, "id_entidade": str})


def geographic(level, scope):
    geo = gpd.read_file(DATA / "referencias.gpkg", layer=level)
    if scope.endswith("_MG"):
        geo = geo[geo.sigla_uf == "MG"]
    return geo.to_crs(5880)


def finish(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[Figura] {path.relative_to(ROOT)}", flush=True)


def overview():
    FIG.mkdir(parents=True, exist_ok=True)
    indicators, profiles = read("indicadores_municipais.csv"), read("perfis_municipais.csv")
    global_results = read("moran_global.csv")
    for scope in ["presidente_BR", "deputado_federal_MG"]:
        geo = geographic("municipio", scope).merge(indicators[["cd_mun", "ips_homicidios", "ips_nota_mediana_enem"]],
                                                   on="cd_mun", how="left", validate="one_to_one")
        fig, axes = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
        for ax, field, title, cmap in zip(axes, ["ips_homicidios", "ips_nota_mediana_enem"],
                                        ["Homicidios", "Nota mediana do ENEM"], ["OrRd", "viridis"]):
            geo.plot(column=field, ax=ax, cmap=cmap, linewidth=0, legend=True,
                     missing_kwds={"color": "lightgray", "label": "Sem dados"},
                     legend_kwds={"shrink": .6})
            ax.set_title(title)
            ax.set_axis_off()
        fig.suptitle(f"Seguranca e educacao | {scope}")
        fig.supxlabel("Fonte: IPS Brasil 2026 / Parte 1; limites BDG-IBGE; SIRGAS 2000 / Brazil Polyconic (EPSG:5880).")
        finish(fig, FIG / f"indicadores_{scope}.png")
        pro = profiles[profiles.escopo == scope]
        geo = geographic("municipio", scope).merge(pro[["cd_mun", "perfil"]], on="cd_mun", validate="one_to_one")
        palette = {"homicidios_acima__enem_acima": "#7b3294", "homicidios_acima__enem_abaixo": "#c51b7d",
                   "homicidios_abaixo__enem_acima": "#008837", "homicidios_abaixo__enem_abaixo": "#80cdc1",
                   "sem_dados": "#cccccc"}
        fig, ax = plt.subplots(figsize=(9, 9), layout="constrained")
        for label in sorted(geo.perfil.unique()):
            group = geo[geo.perfil == label]
            group.plot(ax=ax, color=palette[label], linewidth=0)
            ax.scatter([], [], color=palette[label], marker="s", label=f"{label.replace('__', ' / ').replace('_', ' ')} (n={len(group)})")
        ax.legend(loc="lower left", fontsize=8)
        ax.set_axis_off()
        ax.set_title(f"Perfis municipais por medianas | {scope}")
        fig.supxlabel("Medianas calculadas separadamente para Brasil e MG; igualdade entra em acima. Fonte: Parte 1 / BDG.")
        finish(fig, FIG / f"perfis_{scope}.png")
        fig, axes = plt.subplots(2, 4, figsize=(16, 7), layout="constrained", sharex=True)
        for row, kind in enumerate(["candidato", "partido"]):
            for col, (level, (_, title)) in enumerate(LEVELS.items()):
                values = global_results[(global_results.escopo == scope) & (global_results.tipo == kind)
                                        & (global_results.nivel == level) & (global_results.status == "ok")].moran_i
                ax = axes[row, col]
                if len(values):
                    ax.hist(values, bins=min(20, max(3, len(values))), color="#2b8cbe", edgecolor="white")
                else:
                    ax.text(.5, .5, "Sem teste: amostra insuficiente", transform=ax.transAxes, ha="center", wrap=True)
                ax.set_title(f"{kind} / {title}", fontsize=10)
                ax.set_xlabel("I de Moran")
                ax.set_ylabel("Numero de series")
        fig.suptitle(f"Resultados completos de autocorrelacao | {scope}")
        finish(fig, FIG / f"panorama_moran_{scope}.png")


def extract(scope, candidate=None, party=None):
    kind = "candidato" if candidate is not None else "partido"
    key = "sq_candidato" if kind == "candidato" else "nr_partido"
    catalog = read(f"catalogo_{'candidatos' if kind == 'candidato' else 'partidos'}.csv")
    catalog = catalog[catalog.escopo == scope]
    query = str(candidate if candidate is not None else party)
    match = ((catalog.sq_candidato == query) | (catalog.nr_candidato == query)) if kind == "candidato" else (
        (catalog.nr_partido == query) | (catalog.sg_partido.str.upper() == query.upper()))
    selected = catalog[match]
    if len(selected) != 1:
        raise ValueError("Selecao ausente ou ambigua; consultar catalogo e usar identificador exato")
    entity = str(selected.iloc[0][key])
    label = selected.iloc[0]["nm_candidato" if kind == "candidato" else "sg_partido"]
    dest = FIG / scope / f"{kind}_{entity}"
    dest.mkdir(parents=True, exist_ok=True)
    data = read(f"votacao_{'candidatos' if kind == 'candidato' else 'partidos'}.csv.gz")
    data = data[(data.escopo == scope) & (data[key] == entity)]
    data.to_csv(dest / "votacao.csv", index=False, encoding="utf-8-sig")
    for name in ["moran_global.csv", "correlacoes.csv", "comparacao_escalas.csv", "votacao_por_perfil.csv"]:
        results = read(name)
        results = results[(results.escopo == scope) & (results.tipo == kind) & (results.id_entidade == entity)]
        results.to_csv(dest / name, index=False, encoding="utf-8-sig")
    results = pd.read_csv(dest / "moran_global.csv").set_index("nivel")
    fig, axes = plt.subplots(2, 2, figsize=(13, 13), layout="constrained")
    norm = Normalize(0, max(float(data.percentual.max()), .001))
    for ax, (level, (geokey, title)) in zip(axes.flat, LEVELS.items()):
        geo = geographic(level, scope).merge(data[data.nivel == level], left_on=geokey, right_on="codigo_geo",
                                              how="left", validate="one_to_one")
        geo.plot(column="percentual", ax=ax, cmap="viridis", norm=norm, linewidth=0,
                 missing_kwds={"color": "lightgray"})
        row = results.loc[level]
        statistic = f"I={row.moran_i:.3f}; p={row.p_perm_bilateral:.3f}; q={row.q_fdr_bh:.3f}" if row.status == "ok" else row.status
        ax.set_title(f"{title}\n{statistic}", fontsize=10)
        ax.set_axis_off()
    fig.colorbar(ScalarMappable(norm=norm, cmap="viridis"), ax=list(axes.flat), shrink=.55,
                 label="Percentual dos votos nominais + legenda")
    fig.suptitle(f"{label} | {scope} | primeiro turno 2026")
    fig.supxlabel("TSE / BDG-IBGE; mesma escala de cores nos quatro paineis; EPSG:5880. Ilhas excluidas apenas dos testes.")
    finish(fig, dest / "mapas_quatro_niveis.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escopo", choices=["presidente_BR", "deputado_federal_MG"])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--candidato")
    selection.add_argument("--partido")
    args = parser.parse_args()
    if args.candidato is not None or args.partido is not None:
        if not args.escopo:
            parser.error("--escopo e obrigatorio para extrair uma entidade")
        extract(args.escopo, args.candidato, args.partido)
    else:
        overview()
