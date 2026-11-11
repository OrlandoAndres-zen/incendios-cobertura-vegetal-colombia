"""
Tamaño de los incendios por región natural y fase ENSO (descriptivo).

Ejecutar desde entrega_incendios/ con el entorno activo:
    python tamanos_region_ENSO.py

Qué hace:
  1. Toma el escenario principal con area_total > 0 (ceros y ausentes quedan fuera).
  2. Asigna cada departamento a una región natural (diccionario REGIONES, editable).
  3. Pega la fase ENSO de cada mes desde resultados/serie_mensual_con_ONI.csv.
  4. Calcula n, mediana, p75, p90, p95, p99, máximo y suma por región y fase.
  5. Repite el cálculo solo con meses de temporada seca (dic-mar) para
     comparar en una misma época del año.

Es descriptivo: no prueba causalidad.
area_total está en hectáreas (IDEAM, radicado 20265000183351).
Solo entran en las fases ENSO los anios hasta ANIO_MAX_ENSO (2024); el resto queda "Sin fase".
"""
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
MIN_N = 30                 # menos de 30 registros en una celda: no es confiable
MESES_SECOS = [12, 1, 2, 3]  # elección propia, editable
ANIO_MAX_ENSO = 2024         # ultimo anio que entra en las comparaciones ENSO

# Cada departamento va completo a una sola región (simplificación).
# Cauca y Nariño también tienen zona andina; aquí van en Pacífica.
REGIONES = {
    "Orinoquía": ["ARAUCA", "CASANARE", "META", "VICHADA"],
    "Amazonía": ["AMAZONAS", "CAQUETA", "GUAINIA", "GUAVIARE", "PUTUMAYO", "VAUPES"],
    "Caribe": ["ATLANTICO", "BOLIVAR", "CESAR", "CORDOBA", "LA GUAJIRA",
               "MAGDALENA", "SUCRE"],
    "Pacífica": ["CAUCA", "CHOCO", "NARINO", "VALLE DEL CAUCA"],
    "Andina": ["ANTIOQUIA", "BOYACA", "CALDAS", "CUNDINAMARCA", "HUILA",
               "NORTE DE SANTANDER", "QUINDIO", "RISARALDA", "SANTANDER", "TOLIMA"],
}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


MAPA = {normalizar(d): r for r, ds in REGIONES.items() for d in ds}


def region_de(nombre):
    n = normalizar(nombre)
    if n.startswith("BOGOTA"):
        return "Andina"
    if "SAN ANDRES" in n:
        return "Caribe"
    return MAPA.get(n, "SIN REGION")


# 1. Carga ---------------------------------------------------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
df = df[
    df["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
].copy()
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df = df[df["area_total"] > 0].copy()
print(f"Registros con área positiva: {len(df)}")  # esperado 41746

df["region"] = df["departamento"].map(region_de)
sin_region = df.loc[df["region"] == "SIN REGION", "departamento"].value_counts()
if len(sin_region):
    print("\nAVISO: departamentos sin región (agrégalos a REGIONES):")
    print(sin_region.to_string())

# 2. Fase ENSO por mes ---------------------------------------------------------
oni = pd.read_csv(RES / "serie_mensual_con_ONI.csv")
oni = oni[["anio", "mes", "fase_episodio"]].drop_duplicates(["anio", "mes"])
oni["anio"] = pd.to_numeric(oni["anio"], errors="coerce").astype("Int64")
oni["mes"] = pd.to_numeric(oni["mes"], errors="coerce").astype("Int64")

df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
df["mes"] = pd.to_numeric(df["mes"], errors="coerce").astype("Int64")
df = df.merge(oni, on=["anio", "mes"], how="left")
df["fase_episodio"] = df["fase_episodio"].fillna("Sin fase")
# Regla del proyecto (FUENTES.md): el analisis ENSO usa 2002-2024; 2025 no entra
# en las comparaciones principales. Se cambia ANIO_MAX_ENSO para modificarla.
pasan = (df["anio"] > ANIO_MAX_ENSO) & (df["fase_episodio"] != "Sin fase")
print(f"Registros de {ANIO_MAX_ENSO + 1} en adelante pasados a 'Sin fase': {int(pasan.sum())}")
df.loc[df["anio"] > ANIO_MAX_ENSO, "fase_episodio"] = "Sin fase"
print("\nRegistros por fase ENSO:")
print(df["fase_episodio"].value_counts().to_string())


# 3. Resumen por región y fase ---------------------------------------------------
def tabla(datos):
    g = datos.groupby(["region", "fase_episodio"])["area_total"]
    return g.agg(
        n="size",
        mediana="median",
        p75=lambda s: s.quantile(0.75),
        p90=lambda s: s.quantile(0.90),
        p95=lambda s: s.quantile(0.95),
        p99=lambda s: s.quantile(0.99),
        maximo="max",
        suma_area="sum",
    ).reset_index()


def mostrar(t, metrica, titulo):
    p = t.pivot(index="region", columns="fase_episodio", values=metrica)
    n = t.pivot(index="region", columns="fase_episodio", values="n")
    txt = p.copy().astype(object)
    for r in p.index:
        for c in p.columns:
            v, k = p.loc[r, c], n.loc[r, c]
            if pd.isna(v):
                txt.loc[r, c] = "-"
            else:
                marca = "*" if k < MIN_N else ""
                txt.loc[r, c] = f"{v:,.1f}{marca}"
    print(f"\n{titulo}")
    print(txt.to_string())


todos = tabla(df)
todos.to_csv(RES / "tamanos_por_region_ENSO.csv", index=False, encoding="utf-8-sig")
secos = tabla(df[df["mes"].isin(MESES_SECOS)])
secos.to_csv(RES / "tamanos_por_region_ENSO_dic_mar.csv", index=False, encoding="utf-8-sig")

for nombre, t in [("TODOS LOS MESES", todos), ("SOLO DIC-MAR", secos)]:
    print("\n" + "=" * 60)
    print(nombre)
    mostrar(t, "n", "Número de registros (n):")
    mostrar(t, "mediana", "Mediana de area_total:")
    mostrar(t, "p90", "Percentil 90 de area_total:")
print(f"\n* = menos de {MIN_N} registros en la celda: no es confiable.")

# 4. Gráfica: mediana y p90 por región y fase (todos los meses) ------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, metrica in zip(axes, ["mediana", "p90"]):
    p = todos.pivot(index="region", columns="fase_episodio", values=metrica)
    p.plot(kind="bar", ax=ax, logy=True, rot=30)
    ax.set_title(f"{metrica} de area_total por región y fase ENSO")
    ax.set_xlabel("")
    ax.set_ylabel("hectáreas")
    ax.grid(True, axis="y", which="both", alpha=0.3)
fig.tight_layout()
fig.savefig(RES / "tamanos_region_ENSO.png", dpi=150)

print("\nGuardado: tamanos_por_region_ENSO.csv, tamanos_por_region_ENSO_dic_mar.csv, tamanos_region_ENSO.png")
