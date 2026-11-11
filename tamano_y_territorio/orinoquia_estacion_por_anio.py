"""
Orinoquía: tamaño por fase ENSO en la estación seca de cada departamento,
con la comprobación por año (descriptivo).

Estación seca por departamento (CHIRPS 1991-2020; mes seco = lluvia media del mes < 75 %
de la media mensual): Arauca, Casanare y Vichada dic-mar; Meta dic-feb.
Solo entran registros del escenario principal con area_total > 0 (hectáreas) y fase
ENSO asignada (2002-2024, fase del mes del registro, sin rezago).

Qué calcula:
  1. Dos casos (estación seca): todos los años con fase, y sin 2024 ni 2025.
     Por fase: n, mediana, p75, p90, p99, máximo, y p90 y p99 sin los 6 registros grandes.
  2. Registros por año y fase (para ver si fase y año se confunden).
  3. Por departamento: n, mediana y p90 por fase.
No modifica ningún archivo existente.

Uso (dentro de entrega_incendios, con el .venv activo):
    python orinoquia_estacion_por_anio.py
"""
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
ANIO_MAX_ENSO = 2024
MIN_N = 30
MESES_SECOS = {"ARAUCA": [12, 1, 2, 3], "CASANARE": [12, 1, 2, 3],
               "VICHADA": [12, 1, 2, 3], "META": [12, 1, 2]}
SEIS = {  # (hoja, fila_excel, área esperada)
    "M-12": ("BD_ICV_2010_2020", 16923, 11000.0), "M-14": ("BD_ICV_2010_2020", 16922, 10000.0),
    "M-16": ("BD_ICV_2021", 755, 41079.0), "M-17": ("BD_ICV_2022", 251, 35463.0),
    "M-18": ("BD_ICV_2022", 176, 26008.0), "M-24": ("BD_ICV_2022", 452, 12000.0),
}
FASES = ["El Nino", "La Nina", "Neutral"]


def norm(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
d = d[d["usar_principal"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "si", "sí"])].copy()
d["area_total"] = pd.to_numeric(d["area_total"], errors="coerce")
d["dep"] = d["departamento"].map(norm)
o = d[d["dep"].isin(MESES_SECOS) & (d["area_total"] > 0)].copy()
print("Orinoquía con área positiva:", len(o), "(control: 4902)")

o["anio"] = pd.to_numeric(o["anio"], errors="coerce")
o["mes"] = pd.to_numeric(o["mes"], errors="coerce")
oni = pd.read_csv(RES / "serie_mensual_con_ONI.csv")[["anio", "mes", "fase_episodio"]].drop_duplicates(["anio", "mes"])
o = o.merge(oni, on=["anio", "mes"], how="left")
o["fase"] = o["fase_episodio"].fillna("Sin fase")
o.loc[o["anio"] > ANIO_MAX_ENSO, "fase"] = "Sin fase"


def estacion(r):
    if pd.isna(r["mes"]):
        return "Sin mes"
    return "Seca" if int(r["mes"]) in MESES_SECOS[r["dep"]] else "Resto"


o["estacion"] = o.apply(estacion, axis=1)
print("Estación:", o["estacion"].value_counts().to_dict(), "(control: Seca 4242, Resto 649, Sin mes 11)")

# Los 6 registros grandes
o["hoja_n"] = o["hoja"].astype(str).str.strip()
o["es6"] = False
for k, (hoja, fila, esp) in SEIS.items():
    m = (o["hoja_n"] == hoja) & (pd.to_numeric(o["fila_excel"], errors="coerce") == fila)
    if m.sum() != 1 or abs(float(o.loc[m, "area_total"].iloc[0]) - esp) > 1e-6:
        print(f"  AVISO: {k} no se encontró bien ({int(m.sum())} filas)")
    o.loc[m, "es6"] = True
print("Los 6 registros grandes encontrados:", int(o["es6"].sum()), "(control: 6)")
seca = o[o["estacion"] == "Seca"].copy()
print("De los 6, en estación seca:", int(seca["es6"].sum()))
print("Seca por fase:", seca["fase"].value_counts().to_dict(),
      "(control: El Nino 1787, La Nina 925, Neutral 1018, Sin fase 512)")


def resumen(s):
    a = s["area_total"]
    b = s[~s["es6"]]["area_total"]
    return {"n": len(a), "mediana": a.median(), "p75": a.quantile(.75), "p90": a.quantile(.90),
            "p99": a.quantile(.99), "maximo": a.max(), "p90_sin6": b.quantile(.90), "p99_sin6": b.quantile(.99)}


casos = {"seca, todos los años": seca[seca["fase"].isin(FASES)],
         "seca, sin 2024 ni 2025": seca[seca["fase"].isin(FASES) & (seca["anio"] <= 2023)]}
filas = []
for nom, sub in casos.items():
    for f in FASES:
        r = resumen(sub[sub["fase"] == f]); r.update(caso=nom, fase=f); filas.append(r)
t1 = pd.DataFrame(filas)[["caso", "fase", "n", "mediana", "p75", "p90", "p99", "maximo", "p90_sin6", "p99_sin6"]]
t1.to_csv(RES / "orinoquia_estacion_casos.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", None)
print("\nCASOS (estación seca de cada departamento; hectáreas):")
print(t1.round(1).to_string(index=False))
print("(sin 2024 ni 2025: cada n debe ser MENOR que con dic-mar: 1330 El Nino, 988 La Nina, 1021 Neutral)")

# Por año
conf = seca[seca["fase"].isin(FASES)]
pa = conf.groupby(["anio", "fase"])["area_total"].agg(n="size", mediana="median").reset_index()
pa.to_csv(RES / "orinoquia_estacion_por_anio_fase.csv", index=False, encoding="utf-8-sig")
tab = pa.pivot(index="anio", columns="fase", values="n").fillna(0).astype(int)
print("\nREGISTROS POR AÑO Y FASE (estación seca):")
print(tab.to_string())
ln = pa[(pa["fase"] == "La Nina") & (pa["n"] >= MIN_N)]
print(f"\nLa Niña: años con n >= {MIN_N}: {len(ln)}; esos años reúnen {int(ln['n'].sum())} de {int(tab['La Nina'].sum())} registros.")
for f in FASES:
    x = pa[pa["fase"] == f]
    print(f"{f}: años con registros {len(x)}, con n >= {MIN_N}: {int((x['n'] >= MIN_N).sum())}")

# Por departamento
pdp = conf.groupby(["dep", "fase"])["area_total"].agg(
    n="size", mediana="median", p90=lambda s: s.quantile(.9)).reset_index()
pdp.to_csv(RES / "orinoquia_estacion_por_departamento.csv", index=False, encoding="utf-8-sig")
print("\nPOR DEPARTAMENTO (estación seca): n; mediana; p90")
for dep in sorted(MESES_SECOS):
    txt = []
    for f in FASES:
        r = pdp[(pdp["dep"] == dep) & (pdp["fase"] == f)]
        txt.append(f"{f}: " + (f"{int(r['n'].iloc[0])}{'*' if r['n'].iloc[0] < MIN_N else ''}; {r['mediana'].iloc[0]:.1f}; {r['p90'].iloc[0]:.1f}" if len(r) else "-"))
    print(f"  {dep:9} " + " | ".join(txt))
print("* = menos de 30 registros: no es confiable.")
print("\nGuardado: orinoquia_estacion_casos.csv, orinoquia_estacion_por_anio_fase.csv, orinoquia_estacion_por_departamento.csv")
