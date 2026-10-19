"""Calcula a mesma analise para TODOS os candidatos com votos e todos os partidos.

Saidas: Moran global em quatro niveis, Pearson/Spearman e Moran bivariado
municipais, comparacao de escalas e perfis municipais (item 6e do enunciado).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import warnings

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1] / ".cache"))
import numpy as np
import pandas as pd
from scipy import stats
from esda import Moran, Moran_BV
from esda.significance import calculate_significance
from libpysal.weights import W

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Dados processados/parte2"
LEVELS = {"municipio": "cd_mun", "rgi": "cd_rgi", "rgint": "cd_rgint", "uf": "sigla_uf"}
VARIABLES = ["ips_homicidios", "ips_nota_mediana_enem", "ideb_anos_iniciais", "ideb_anos_finais",
             "ideb_ensino_medio", "pib_per_capita", "censo2022_rendimento_medio", "densidade_censo2022"]


def read(name):
    return pd.read_csv(OUT / name, dtype={"codigo_geo": str, "sq_candidato": str, "nr_partido": str,
                                        "cd_mun": str, "cd_rgi": str, "cd_rgint": str,
                                        "origem": str, "destino": str})


def save(frame, name):
    frame.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.10g")


def spatial_weights(codes, edges):
    """Induz subgrafo no conjunto observado; remove ilhas sem inventar vizinhos."""
    ids = sorted(set(codes))
    neighbors = {code: [] for code in ids}
    for a, b in edges[["origem", "destino"]].itertuples(index=False, name=None):
        if a in neighbors and b in neighbors:
            neighbors[a].append(b)
            neighbors[b].append(a)
    islands = [code for code in ids if not neighbors[code]]
    neighbors = {code: near for code, near in neighbors.items() if near}
    if len(neighbors) < 3:
        return None, islands
    w = W(neighbors, id_order=sorted(neighbors), silence_warnings=True)
    w.transform = "r"
    return w, islands


def two_sided(observed, simulations):
    """Dois lados explicitamente: nao confundir p_sim legado do PySAL com bilateral."""
    return float(calculate_significance(observed, simulations, alternative="two-sided"))


def adjust_fdr(frame, p, q, grouping):
    frame[q] = np.nan
    for _, indexes in frame.groupby(grouping, dropna=False).groups.items():
        valid = frame.loc[indexes, p].dropna()
        if len(valid):
            frame.loc[valid.index, q] = stats.false_discovery_control(valid.to_numpy(), method="bh")


def analyze(permutations, seed):
    started = time.monotonic()
    np.random.seed(seed)
    edges = read("vizinhos.csv")
    indicators = read("indicadores_municipais.csv")
    indicators["densidade_censo2022"] = indicators.censo2022_populacao / indicators.area_km2
    catalogs = {"candidato": read("catalogo_candidatos.csv"), "partido": read("catalogo_partidos.csv")}
    inputs = {"candidato": read("votacao_candidatos.csv.gz"), "partido": read("votacao_partidos.csv.gz")}
    global_rows, correlations, diagnostics = [], [], []
    for kind, data in inputs.items():
        entity_col = "sq_candidato" if kind == "candidato" else "nr_partido"
        for scope in sorted(data.escopo.unique()):
            subset = data[data.escopo == scope]
            for level in LEVELS:
                block = subset[subset.nivel == level]
                matrix = block.pivot(index="codigo_geo", columns=entity_col, values="percentual").sort_index()
                if matrix.isna().any().any():
                    raise ValueError("Grade eleitoral incompleta: falta explicitar zeros")
                w, islands = spatial_weights(matrix.index, edges[edges.nivel == level])
                diagnostics.append({"escopo": scope, "tipo": kind, "nivel": level,
                                    "variavel": "percentual_votos", "n_total": len(matrix),
                                    "n_espacial": w.n if w else 0, "ilhas": len(islands),
                                    "codigos_ilhas": ";".join(islands),
                                    "componentes": w.n_components if w else 0})
                print(f"[Moran] {scope} / {kind} / {level}: {matrix.shape[1]} series", flush=True)
                for entity in matrix.columns:
                    row = {"escopo": scope, "tipo": kind, "id_entidade": entity, "nivel": level,
                           "n_total": len(matrix), "n_espacial": w.n if w else 0, "ilhas": len(islands),
                           "moran_i": np.nan, "i_esperado": np.nan, "p_perm_bilateral": np.nan,
                           "status": "n_espacial_insuficiente"}
                    if w:
                        x = matrix.loc[w.id_order, entity].to_numpy(float)
                        if np.ptp(x) == 0:
                            row["status"] = "variavel_constante"
                        else:
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore", RuntimeWarning)
                                mi = Moran(x, w, permutations=permutations)
                            row.update(moran_i=float(mi.I), i_esperado=float(mi.EI),
                                       p_perm_bilateral=two_sided(mi.I, mi.sim), status="ok")
                    global_rows.append(row)
                if level != "municipio":
                    continue
                muni = indicators.set_index("cd_mun").reindex(matrix.index)
                for variable in VARIABLES:
                    y_all = pd.to_numeric(muni[variable], errors="coerce")
                    present = np.isfinite(y_all)
                    observed_ids = matrix.index[present]
                    wv, missing_islands = spatial_weights(observed_ids, edges[edges.nivel == "municipio"])
                    diagnostics.append({"escopo": scope, "tipo": kind, "nivel": level,
                                        "variavel": variable, "n_total": len(observed_ids),
                                        "n_espacial": wv.n if wv else 0, "ilhas": len(missing_islands),
                                        "codigos_ilhas": ";".join(missing_islands),
                                        "componentes": wv.n_components if wv else 0})
                    print(f"[Correlacao] {scope} / {kind} / {variable}", flush=True)
                    for entity in matrix.columns:
                        row = {"escopo": scope, "tipo": kind, "id_entidade": entity, "variavel": variable,
                               "n_correlacao": len(observed_ids), "n_espacial": wv.n if wv else 0,
                               "faltantes": int((~present).sum()), "pearson_r": np.nan,
                               "pearson_p": np.nan, "spearman_rho": np.nan, "spearman_p": np.nan,
                               "moran_bivariado": np.nan, "p_perm_bilateral": np.nan,
                               "status": "variavel_constante_ou_amostra_insuficiente"}
                        x, y = matrix.loc[observed_ids, entity].to_numpy(float), y_all.loc[observed_ids].to_numpy(float)
                        if len(x) >= 3 and np.ptp(x) > 0 and np.ptp(y) > 0:
                            pr, sp = stats.pearsonr(x, y), stats.spearmanr(x, y)
                            row.update(pearson_r=float(pr.statistic), pearson_p=float(pr.pvalue),
                                       spearman_rho=float(sp.statistic), spearman_p=float(sp.pvalue),
                                       status="sem_amostra_espacial")
                            if wv:
                                xs = matrix.loc[wv.id_order, entity].to_numpy(float)
                                ys = y_all.loc[wv.id_order].to_numpy(float)
                                if np.ptp(xs) > 0 and np.ptp(ys) > 0:
                                    mi = Moran_BV(xs, ys, wv, permutations=permutations)
                                    row.update(moran_bivariado=float(mi.I),
                                               p_perm_bilateral=two_sided(mi.I, mi.sim), status="ok")
                        correlations.append(row)
                # Checkpoints permitem acompanhar uma execucao completa sem alterar o metodo.
                save(pd.DataFrame(global_rows), "moran_global_parcial.csv")
                save(pd.DataFrame(correlations), "correlacoes_parcial.csv")
    global_frame, corr_frame = pd.DataFrame(global_rows), pd.DataFrame(correlations)
    adjust_fdr(global_frame, "p_perm_bilateral", "q_fdr_bh", ["escopo", "tipo", "nivel"])
    for p, q in [("p_perm_bilateral", "q_fdr_bh"), ("pearson_p", "pearson_q_fdr_bh"),
                 ("spearman_p", "spearman_q_fdr_bh")]:
        adjust_fdr(corr_frame, p, q, ["escopo", "tipo", "variavel"])
    for kind, catalog in catalogs.items():
        key = "sq_candidato" if kind == "candidato" else "nr_partido"
        catalog = catalog.rename(columns={key: "id_entidade"})
        for frame in [global_frame, corr_frame]:
            mask = frame.tipo == kind
            # Usar apenas as chaves: outros metadados ja inseridos no DataFrame
            # criariam sufixos _x/_y ao integrar o catalogo de partidos.
            enriched = frame.loc[mask, ["escopo", "id_entidade"]].merge(
                catalog, on=["escopo", "id_entidade"], how="left", validate="many_to_one")
            for col in catalog.columns.difference(["escopo", "id_entidade"]):
                if col not in frame:
                    frame[col] = pd.Series(index=frame.index, dtype="object")
                frame.loc[mask, col] = enriched[col].to_numpy()
    save(global_frame, "moran_global.csv")
    save(corr_frame, "correlacoes.csv")
    save(pd.DataFrame(diagnostics), "diagnostico_pesos.csv")
    # Uma linha por entidade para comparar os mesmos dados em diferentes escalas (6b).
    scale = global_frame.pivot(index=["escopo", "tipo", "id_entidade"], columns="nivel",
                               values=["moran_i", "p_perm_bilateral", "q_fdr_bh"])
    scale.columns = [f"{value}_{level}" for value, level in scale.columns]
    save(scale.reset_index(), "comparacao_escalas.csv")
    profiles(inputs, indicators)
    metadata = {"permutacoes": permutations, "semente": seed, "medida_eleitoral": "percentual nominal + legenda",
                "vizinhos": "Queen por ST_Touches nas geometrias originais do BDG; pesos por linha",
                "ilhas": "excluidas apenas dos testes espaciais; mantidas nas tabelas e correlacoes comuns",
                "p_valor": "bilateral, esda.significance.calculate_significance",
                "fdr": "Benjamini-Hochberg por escopo/tipo/nivel ou escopo/tipo/indicador",
                "moran_bivariado": "x = percentual eleitoral; lag espacial do indicador y; permuta y",
                "linhas_moran": len(global_frame), "linhas_correlacoes": len(corr_frame),
                "segundos": round(time.monotonic() - started, 2)}
    (OUT / "metodo_analise.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(f"[OK] {len(global_frame)} linhas Moran; {len(corr_frame)} correlacoes", flush=True)


def profiles(inputs, indicators):
    """Item 6e: quatro perfis descritivos por medianas, sem ajuste de modelos."""
    assignments, summaries, cutoffs = [], [], []
    for scope in sorted(inputs["candidato"].escopo.unique()):
        base = indicators if scope == "presidente_BR" else indicators[indicators.sigla_uf == "MG"]
        complete = base.dropna(subset=["ips_homicidios", "ips_nota_mediana_enem"])
        h, e = complete.ips_homicidios.median(), complete.ips_nota_mediana_enem.median()
        frame = base[["cd_mun", "ips_homicidios", "ips_nota_mediana_enem"]].copy()
        frame["perfil"] = np.where(frame.ips_homicidios >= h, "homicidios_acima", "homicidios_abaixo")
        frame["perfil"] += np.where(frame.ips_nota_mediana_enem >= e, "__enem_acima", "__enem_abaixo")
        frame.loc[frame[["ips_homicidios", "ips_nota_mediana_enem"]].isna().any(axis=1), "perfil"] = "sem_dados"
        frame["escopo"] = scope
        assignments.append(frame)
        cutoffs.append({"escopo": scope, "mediana_homicidios": h, "mediana_enem": e,
                        "municipios_com_dados": len(complete), "regra_empate": "igual a mediana entra em acima"})
        for kind, data in inputs.items():
            key = "sq_candidato" if kind == "candidato" else "nr_partido"
            block = data[(data.escopo == scope) & (data.nivel == "municipio")].merge(
                frame[["cd_mun", "perfil"]], left_on="codigo_geo", right_on="cd_mun", validate="many_to_one")
            summary = block.groupby([key, "perfil"], as_index=False).agg(
                votos=("votos", "sum"), denominador=("denominador", "sum"), municipios=("codigo_geo", "nunique"))
            summary["percentual"] = 100 * summary.votos / summary.denominador
            summaries.append(summary.rename(columns={key: "id_entidade"}).assign(escopo=scope, tipo=kind))
    save(pd.concat(assignments, ignore_index=True), "perfis_municipais.csv")
    save(pd.concat(summaries, ignore_index=True), "votacao_por_perfil.csv")
    save(pd.DataFrame(cutoffs), "limiares_perfis.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--permutacoes", type=int, default=999)
    parser.add_argument("--semente", type=int, default=2026)
    args = parser.parse_args()
    if args.permutacoes < 99:
        parser.error("Use pelo menos 99 permutacoes; a execucao final utiliza 999")
    analyze(args.permutacoes, args.semente)
