"""Parte 2: dados completos, primeiro turno; presidente/BR e deputado federal/MG.

Uso local: .venv/bin/python scripts/03_preparar_parte2.py
Exportacao somente leitura do BDG: acrescentar --exportar-referencias.
Nao executa o script de carga da Parte 1 e nao modifica tabelas do servidor.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Dados processados" / "parte2"
LEVELS = {"municipio": "cd_mun", "rgi": "cd_rgi", "rgint": "cd_rgint", "uf": "sigla_uf"}
SCOPES = {"presidente_BR": ("1", "BR"), "deputado_federal_MG": ("6", "MG")}
SPECIAL = {"95": "brancos", "96": "nulos", "97": "anulados_separados"}


def save(frame, name):
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.10g")


def export_references():
    """Geometrias simplificadas para desenho; vizinhos nas geometrias ORIGINAIS."""
    import geopandas as gpd
    import psycopg
    from psycopg.rows import dict_row
    from shapely import from_wkb

    OUT.mkdir(parents=True, exist_ok=True)
    provenance = {"obtido_em_utc": datetime.now(timezone.utc).isoformat(), "tabelas": []}
    with psycopg.connect(
        host=os.getenv("PGHOST", "150.164.2.42"), port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "bdg2026"), user=os.getenv("PGUSER", "turma2026"),
        password=os.getenv("PGPASSWORD", "turma"), connect_timeout=15,
        options="-c default_transaction_read_only=on", row_factory=dict_row,
    ) as conn:
        edges = []
        for level, table in [("municipio", "munic"), ("rgi", "micro"), ("rgint", "meso"), ("uf", "estado")]:
            key = LEVELS[level]
            cols = {"municipio": "cd_mun,nm_mun,cd_rgi,cd_rgint,sigla_uf",
                    "rgi": "cd_rgi,nm_rgi,cd_rgint,sigla_uf",
                    "rgint": "cd_rgint,nm_rgint,sigla_uf", "uf": "sigla_uf,nm_uf"}[level]
            exclusion = "WHERE cd_mun NOT IN ('4300001','4300002')" if level == "municipio" else ""
            print(f"[BDG] exportando geodata.{table}", flush=True)
            rows = conn.execute(
                f"SELECT {cols}, ST_SRID(geom) AS srid, "
                f"ST_AsBinary(ST_SimplifyPreserveTopology(geom,0.001)) AS wkb "
                f"FROM geodata.{table} {exclusion} ORDER BY {key}"
            ).fetchall()
            frame = pd.DataFrame(rows)
            srids = frame.pop("srid").unique()
            if len(srids) != 1 or srids[0] != 4674:
                raise ValueError(f"SRID inesperado: {srids}; revisar tolerancia de desenho")
            geom = from_wkb([bytes(b) for b in frame.pop("wkb")])
            geo = gpd.GeoDataFrame(frame, geometry=geom, crs=int(srids[0]))
            if geo[key].duplicated().any():
                raise ValueError(f"Chave geografica duplicada em {table}")
            geo.to_file(OUT / "referencias.gpkg", layer=level, driver="GPKG")
            # A simplificacao e apenas cartografica: nunca usar para decidir contiguidade.
            print(f"[BDG] contiguidade Queen original: {table}", flush=True)
            exclusions = ("AND a.cd_mun NOT IN ('4300001','4300002') "
                          "AND b.cd_mun NOT IN ('4300001','4300002')") if level == "municipio" else ""
            adjacent = conn.execute(
                f"SELECT a.{key} AS origem,b.{key} AS destino FROM geodata.{table} a "
                f"JOIN geodata.{table} b ON a.{key}<b.{key} AND a.geom && b.geom "
                f"AND ST_Touches(a.geom,b.geom) WHERE TRUE {exclusions} "
                f"ORDER BY a.{key},b.{key}"
            ).fetchall()
            edges.extend({"nivel": level, **r} for r in adjacent)
            provenance["tabelas"].append({"tabela": f"geodata.{table}", "objetos": len(geo),
                                           "pares_vizinhos": len(adjacent)})
        save(pd.DataFrame(edges), "vizinhos.csv")
        sources = {
            "sexo_fx_etaria_simplif": "codigo,municipio,pop_total",
            "renda_trabalho": "codigo,municipio,rendimento_medio_reais,rendimento_mediano_reais",
        }
        for table, cols in sources.items():
            frame = pd.DataFrame(conn.execute(f"SELECT {cols} FROM geodata.{table}").fetchall())
            save(frame, f"censo2022_{table}.csv")
            comment = conn.execute(
                "SELECT obj_description(to_regclass(%s),'pg_class') AS comentario",
                (f"geodata.{table}",),
            ).fetchone()["comentario"]
            provenance["tabelas"].append({"tabela": f"geodata.{table}", "linhas": len(frame),
                                           "comentario": comment})
    (OUT / "fontes_bdg.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
    print("[BDG] referencias locais prontas; servidor nao foi modificado", flush=True)


def read_zip_csv(archive, member, **kwargs):
    with zipfile.ZipFile(ROOT / archive) as z:
        with z.open(member) as stream:
            return pd.read_csv(stream, sep=";", encoding="latin1", dtype=str,
                               keep_default_na=False, **kwargs)


def references():
    ref = pd.read_csv(ROOT / "Dados brutos/ref/munic_ref.csv", dtype=str)
    ref = ref[~ref.cd_mun.isin(["4300001", "4300002"])].copy()
    mapping = read_zip_csv("municipio_tse_ibge.zip", "municipio_tse_ibge.csv")
    mapping["cd_tse"] = mapping.CD_MUNICIPIO_TSE.str.zfill(5)
    mapping = mapping.rename(columns={"CD_MUNICIPIO_IBGE": "cd_mun", "SG_UF": "sigla_uf"})
    if mapping.cd_mun.duplicated().any() or mapping.duplicated(["sigla_uf", "cd_tse"]).any():
        raise ValueError("Mapeamento TSE/IBGE nao e univoco")
    ref["cd_tse"] = ref.cd_tse.map(lambda x: str(int(float(x))).zfill(5))
    check = ref.merge(mapping[["cd_mun", "sigla_uf", "cd_tse"]], on="cd_mun", suffixes=("", "_novo"),
                      how="outer", validate="one_to_one", indicator=True)
    if not check._merge.eq("both").all() or not check.cd_tse.eq(check.cd_tse_novo).all():
        raise ValueError("Referencia Parte 1 diverge do mapeamento TSE/IBGE; revisar antes de analisar")
    return ref


def candidates():
    fields = ["ANO_ELEICAO", "CD_TIPO_ELEICAO", "NR_TURNO", "CD_ELEICAO", "SG_UE", "CD_CARGO",
              "SQ_CANDIDATO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "NR_PARTIDO", "SG_PARTIDO",
              "DS_SIT_TOT_TURNO"]
    # BRASIL ja contem as UFs: nao concatenar novamente os arquivos estaduais.
    all_cand = read_zip_csv("consulta_cand_2026.zip", "consulta_cand_2026_BRASIL.csv", usecols=fields)
    all_cand = all_cand[(all_cand.ANO_ELEICAO == "2026") & (all_cand.NR_TURNO == "1")
                        & (all_cand.CD_TIPO_ELEICAO == "2")]
    catalogs = []
    for scope, (office, ue) in SCOPES.items():
        frame = all_cand[(all_cand.CD_CARGO == office) & (all_cand.SG_UE == ue)].copy()
        frame = frame.drop_duplicates()
        if frame.SQ_CANDIDATO.duplicated().any():
            raise ValueError(f"Registro ambiguo de candidato no primeiro turno: {scope}")
        frame["escopo"] = scope
        catalogs.append(frame)
    cat = pd.concat(catalogs, ignore_index=True).rename(columns={
        "SQ_CANDIDATO": "sq_candidato", "NR_CANDIDATO": "nr_candidato",
        "NM_URNA_CANDIDATO": "nm_candidato", "NR_PARTIDO": "nr_partido", "SG_PARTIDO": "sg_partido",
        "DS_SIT_TOT_TURNO": "situacao_turno", "CD_ELEICAO": "cd_eleicao"})
    cat = cat[["escopo", "cd_eleicao", "sq_candidato", "nr_candidato", "nm_candidato",
               "nr_partido", "sg_partido", "situacao_turno"]].sort_values(["escopo", "sq_candidato"])
    parties = cat[["escopo", "nr_partido", "sg_partido"]].drop_duplicates()
    if parties.duplicated(["escopo", "nr_partido"]).any():
        raise ValueError("Siglas partidarias ambiguas")
    return cat, parties


def aggregate_zip(scope, archive, office, election):
    columns = ["ANO_ELEICAO", "CD_TIPO_ELEICAO", "NR_TURNO", "CD_ELEICAO", "CD_CARGO", "SG_UF",
               "CD_MUNICIPIO", "SQ_CANDIDATO", "NR_VOTAVEL", "QT_VOTOS"]
    totals = Counter()
    audit = {"arquivo": archive, "linhas_lidas": 0, "linhas_escopo": 0, "votos_escopo": 0}
    with zipfile.ZipFile(ROOT / archive) as z:
        member = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(member) as stream:
            chunks = pd.read_csv(stream, sep=";", encoding="latin1", usecols=columns,
                                 dtype=str, keep_default_na=False, chunksize=200_000)
            for chunk in chunks:
                audit["linhas_lidas"] += len(chunk)
                selected = chunk[(chunk.ANO_ELEICAO == "2026") & (chunk.NR_TURNO == "1")
                                 & (chunk.CD_TIPO_ELEICAO == "2") & (chunk.CD_CARGO == office)]
                if selected.empty:
                    continue
                if set(selected.CD_ELEICAO) != {election}:
                    raise ValueError("Eleicao dos votos diverge do cadastro")
                selected = selected.copy()
                selected["QT_VOTOS"] = pd.to_numeric(selected.QT_VOTOS, errors="raise").astype("int64")
                if (selected.QT_VOTOS < 0).any():
                    raise ValueError("Quantidade de votos negativa")
                audit["linhas_escopo"] += len(selected)
                audit["votos_escopo"] += int(selected.QT_VOTOS.sum())
                grouped = selected.groupby(["SG_UF", "CD_MUNICIPIO", "SQ_CANDIDATO", "NR_VOTAVEL"])["QT_VOTOS"].sum()
                totals.update(grouped.to_dict())
                print(f"[{scope}] {audit['linhas_lidas']:,} registros lidos", flush=True)
    rows = pd.DataFrame([(*key, votes) for key, votes in sorted(totals.items())],
                        columns=["sigla_uf", "cd_tse", "sq_candidato", "nr_votavel", "votos"])
    rows["cd_tse"] = rows.cd_tse.str.zfill(5)
    rows["escopo"] = scope
    return rows, audit


def municipal_indicators(ref):
    theme = pd.read_csv(ROOT / "Dados processados/grupo_seguranca_educacao.csv", dtype={
        "cd_mun": str, "cd_rgi": str, "cd_rgint": str, "cd_tse": str})
    frame = ref.merge(theme.drop(columns=[c for c in ref.columns if c != "cd_mun" and c in theme]),
                      on="cd_mun", how="left", validate="one_to_one")
    for table, rename in [
        ("sexo_fx_etaria_simplif", {"pop_total": "censo2022_populacao"}),
        ("renda_trabalho", {"rendimento_medio_reais": "censo2022_rendimento_medio",
                           "rendimento_mediano_reais": "censo2022_rendimento_mediano"}),
    ]:
        path = OUT / f"censo2022_{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Falta {path.name}; execute --exportar-referencias primeiro")
        data = pd.read_csv(path, dtype={"codigo": str})
        # Aceita codigo IBGE de 7 digitos ou prefixo de 6, somente se univoco.
        codes = set(ref.cd_mun)
        prefixes = {k[:6]: k for k in ref.cd_mun}
        if len(prefixes) != len(ref):
            raise ValueError("Prefixos IBGE ambiguos")
        data["cd_mun"] = data.codigo.str.strip().map(
            lambda code: code if code in codes else prefixes.get(code))
        data = data[data.cd_mun.notna()]
        if data.cd_mun.duplicated().any():
            raise ValueError(f"Censo municipal duplicado: {table}")
        data = data[["cd_mun", *rename]].rename(columns=rename)
        for col in rename.values():
            data[col] = pd.to_numeric(data[col], errors="coerce")
            data.loc[data[col] < 0, col] = np.nan
        frame = frame.merge(data, on="cd_mun", how="left", validate="one_to_one")
    save(frame.sort_values("cd_mun"), "indicadores_municipais.csv")
    return frame


def prepare():
    ref = references()
    # Verificar as dependencias antes de ler os ZIPs volumosos.
    indicators = municipal_indicators(ref)
    cat, parties = candidates()
    audit = {"escopos": {}, "denominador": "votos nominais + legenda; exclui codigos 95,96,97",
             "zero": "municipio coberto e candidato sem registro de votos recebe zero"}
    all_votes, all_parties, all_totals, active_catalogs, excluded_catalogs = [], [], [], [], []
    for scope, (office, ue) in SCOPES.items():
        roster = cat[cat.escopo == scope]
        elections = roster.cd_eleicao.unique()
        if len(elections) != 1:
            raise ValueError(f"Mais de uma eleicao no escopo {scope}")
        archive = f"votacao_secao_2026_{ue}.zip"
        raw, audit_scope = aggregate_zip(scope, archive, office, elections[0])
        candidate_totals = raw[raw.sq_candidato.isin(roster.sq_candidato)].groupby("sq_candidato").votos.sum()
        inactive = roster[roster.sq_candidato.map(candidate_totals).fillna(0) == 0].copy()
        inactive["motivo_exclusao"] = "zero votos no escopo completo, incluindo exterior quando presente"
        excluded_catalogs.append(inactive)
        roster = roster[roster.sq_candidato.map(candidate_totals).fillna(0) > 0].copy()
        roster["votos_totais_escopo"] = roster.sq_candidato.map(candidate_totals)
        active_catalogs.append(roster)
        if ue == "MG" and set(raw.sigla_uf) != {"MG"}:
            raise ValueError("UF inesperada no arquivo MG")
        foreign = raw[raw.sigla_uf == "ZZ"]
        save(foreign, f"exterior_{scope}.csv")
        domestic = raw[raw.sigla_uf != "ZZ"].merge(
            ref[["sigla_uf", "cd_tse", "cd_mun", "cd_rgi", "cd_rgint"]],
            on=["sigla_uf", "cd_tse"], how="left", validate="many_to_one")
        unmatched = domestic[domestic.cd_mun.isna()]
        save(unmatched, f"nao_pareados_{scope}.csv")
        if len(unmatched):
            raise ValueError(f"Municipios sem pareamento: {scope}; consultar arquivo de auditoria")
        expected_ref = ref if ue == "BR" else ref[ref.sigla_uf == ue]
        if set(domestic.cd_mun) != set(expected_ref.cd_mun):
            raise ValueError(f"Cobertura municipal incompleta: {scope}; nao imputar municipios ausentes com zero")
        domestic["categoria"] = domestic.nr_votavel.map(SPECIAL).fillna("nominais")
        legend = (domestic.sq_candidato.isin(["-1", "-3"]) & domestic.nr_votavel.str.len().eq(2)
                  & ~domestic.nr_votavel.isin(SPECIAL))
        domestic.loc[legend, "categoria"] = "legenda"
        nominal = domestic[domestic.categoria == "nominais"].merge(
            roster[["sq_candidato", "nr_partido"]], on="sq_candidato", how="left", validate="many_to_one")
        if nominal.nr_partido.isna().any():
            raise ValueError(f"Votos nominais sem cadastro: {scope}")
        legends = domestic[domestic.categoria == "legenda"].assign(nr_partido=lambda x: x.nr_votavel)
        if not set(legends.nr_partido).issubset(set(parties[parties.escopo == scope].nr_partido)):
            raise ValueError("Legenda sem partido no cadastro")
        party_votes = pd.concat([nominal, legends], ignore_index=True)
        for level, key in LEVELS.items():
            geo = sorted(expected_ref[key].unique())
            totals = domestic.groupby([key, "categoria"]).votos.sum().unstack(fill_value=0)
            totals = totals.reindex(index=geo, columns=["nominais", "legenda", *SPECIAL.values()], fill_value=0)
            denominator = totals.nominais + totals.legenda
            if (denominator <= 0).any():
                raise ValueError("Denominador nulo: nao calcular participacao")
            totals["total"] = totals.sum(axis=1)
            totals["denominador"] = denominator
            totals.index.name = "codigo_geo"
            totals = totals.reset_index().assign(escopo=scope, nivel=level)
            all_totals.append(totals)
            counts = nominal.groupby([key, "sq_candidato"]).votos.sum()
            grid = pd.MultiIndex.from_product([geo, sorted(roster.sq_candidato)], names=["codigo_geo", "sq_candidato"])
            counts.index.names = grid.names
            votes = counts.reindex(grid, fill_value=0).rename("votos").reset_index()
            votes["denominador"] = votes.codigo_geo.map(denominator)
            votes["percentual"] = 100 * votes.votos / votes.denominador
            all_votes.append(votes.assign(escopo=scope, nivel=level))
            pc = party_votes.groupby([key, "nr_partido"]).votos.sum()
            pg = pd.MultiIndex.from_product([geo, sorted(parties[parties.escopo == scope].nr_partido)],
                                            names=["codigo_geo", "nr_partido"])
            pc.index.names = pg.names
            pv = pc.reindex(pg, fill_value=0).rename("votos").reset_index()
            pv["denominador"] = pv.codigo_geo.map(denominator)
            pv["percentual"] = 100 * pv.votos / pv.denominador
            all_parties.append(pv.assign(escopo=scope, nivel=level))
            if int(votes.votos.sum()) != int(nominal.votos.sum()):
                raise AssertionError("Agregacao alterou total nominal")
            if int(pv.votos.sum()) != int(party_votes.votos.sum()):
                raise AssertionError("Agregacao alterou total por partido")
            if int(totals.total.sum()) != int(domestic.votos.sum()):
                raise AssertionError("Categorias nao reconciliam com votos domesticos")
        audit_scope.update(votos_exterior=int(foreign.votos.sum()), votos_domesticos=int(domestic.votos.sum()),
                           municipios=int(domestic.cd_mun.nunique()), candidatos=len(roster),
                           candidatos_excluidos_sem_votos=len(inactive),
                           partidos=int(parties[parties.escopo == scope].nr_partido.nunique()),
                           nao_pareados=len(unmatched), categorias={k: int(v) for k, v in domestic.groupby("categoria").votos.sum().items()})
        assert audit_scope["votos_escopo"] == audit_scope["votos_domesticos"] + audit_scope["votos_exterior"]
        audit["escopos"][scope] = audit_scope
    save(pd.concat(active_catalogs, ignore_index=True), "catalogo_candidatos.csv")
    save(pd.concat(excluded_catalogs, ignore_index=True), "candidatos_excluidos_sem_votos.csv")
    save(parties.sort_values(["escopo", "nr_partido"]), "catalogo_partidos.csv")
    save(pd.concat(all_votes, ignore_index=True), "votacao_candidatos.csv.gz")
    save(pd.concat(all_parties, ignore_index=True), "votacao_partidos.csv.gz")
    save(pd.concat(all_totals, ignore_index=True), "totais_votacao.csv")
    audit["indicadores_faltantes"] = {col: int(indicators[col].isna().sum()) for col in indicators
                                       if col.startswith(("ips_", "ideb_", "censo2022_"))}
    (OUT / "auditoria_preparacao.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    print("[OK] todos os candidatos e partidos; quatro niveis; totais reconciliados", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exportar-referencias", action="store_true",
                        help="exporta apenas limites, vizinhos e Censo do BDG, em transacao somente leitura")
    args = parser.parse_args()
    if args.exportar_referencias:
        export_references()
    else:
        prepare()
