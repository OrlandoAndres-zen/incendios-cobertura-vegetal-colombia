"""
Tamaño de los registros por región natural y fase ENSO, EN LA MISMA ESTACIÓN
(descriptivo). Versión de tamanos_region_ENSO.py donde la temporada seca se
define por departamento con la lluvia (CHIRPS 1991-2020; mes seco = precipitación
media del mes por debajo del 75 % de la media mensual del departamento), y no
con diciembre a marzo para todos.

Ejecutar desde entrega_incendios/ con el entorno activo:
    python tamanos_region_ENSO_estacion.py

Qué hace:
  1. Toma el escenario principal con area_total > 0 (hectáreas; ceros y ausentes fuera).
  2. Asigna cada departamento a una región (diccionario REGIONES, editable).
  3. Pega la fase ENSO desde resultados/serie_mensual_con_ONI.csv. REZAGO_FASE = 0
     usa la fase del mes del registro; 1 usa la del mes anterior (sensibilidad).
  4. Clasifica cada registro como Seca o Resto según los meses secos de su departamento.
     Amazonas y San Andrés quedan fuera de "misma estación" (Amazonas no tiene mes seco
     por esta regla y San Andrés no tiene datos de lluvia). Bogotá usa los de Cundinamarca.
  5. Calcula n, mediana, p75, p90, p95, p99, máximo y suma por región y fase,
     por separado para Seca y para Resto.

Es descriptivo: no prueba causalidad. No toca ningún archivo existente.
Solo entran en las fases ENSO los años hasta ANIO_MAX_ENSO (2024); el resto queda "Sin fase".
"""
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
MIN_N = 30            # menos de 30 registros en una celda: no es confiable
ANIO_MAX_ENSO = 2024  # último año que entra en las comparaciones ENSO
REZAGO_FASE = 0       # 0 = fase del mes del registro; 1 = fase del mes anterior

REGIONES = {
    "Orinoquía": ["ARAUCA", "CASANARE", "META", "VICHADA"],
    "Amazonía": ["AMAZONAS", "CAQUETA", "GUAINIA", "GUAVIARE", "PUTUMAYO", "VAUPES"],
    "Caribe": ["ATLANTICO", "BOLIVAR", "CESAR", "CORDOBA", "LA GUAJIRA",
               "MAGDALENA", "SUCRE"],
    "Pacífica": ["CAUCA", "CHOCO", "NARINO", "VALLE DEL CAUCA"],
    "Andina": ["ANTIOQUIA", "BOYACA", "CALDAS", "CUNDINAMARCA", "HUILA",
               "NORTE DE SANTANDER", "QUINDIO", "RISARALDA", "SANTANDER", "TOLIMA"],
}

# Meses secos por departamento (de meses_secos_por_departamento.csv). Los que tienen
# dos épocas (Caldas, Quindío, Tolima) llevan la unión de ambas.
MESES_SECOS = {
    "ANTIOQUIA": [12, 1, 2, 3], "ARAUCA": [12, 1, 2, 3], "ATLANTICO": [12, 1, 2, 3, 4],
    "BOLIVAR": [12, 1, 2, 3], "BOYACA": [12, 1, 2], "CALDAS": [1, 2, 7, 8],
    "CAQUETA": [12, 1, 2], "CASANARE": [12, 1, 2, 3], "CAUCA": [7, 8],
    "CESAR": [12, 1, 2, 3], "CHOCO": [1, 2, 3], "CORDOBA": [12, 1, 2, 3],
    "CUNDINAMARCA": [12, 1, 2], "GUAINIA": [12, 1, 2], "LA GUAJIRA": [12, 1, 2, 3, 4, 7],
    "GUAVIARE": [12, 1, 2], "HUILA": [7, 8, 9], "MAGDALENA": [12, 1, 2, 3],
    "META": [12, 1, 2], "NARINO": [8, 9], "NORTE DE SANTANDER": [12, 1, 2, 3],
    "PUTUMAYO": [1, 2], "QUINDIO": [1, 6, 7, 8], "RISARALDA": [1, 2],
    "SANTANDER": [12, 1, 2], "SUCRE": [12, 1, 2, 3], "TOLIMA": [1, 6, 7, 8],
    "VALLE DEL CAUCA": [1, 2], "VAUPES": [1, 2], "VICHADA": [12, 1, 2, 3],
}
SIN_ESTACION = {"AMAZONAS"}  # y San Andrés (se detecta por el nombre)


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


def estacion_de(dep, mes):
    n = normalizar(dep)
    if n.startswith("BOGOTA"):
        n = "CUNDINAMARCA"
    if "SAN ANDRES" in n or n in SIN_ESTACION or n not in MESES_SECOS:
        return "Sin estación definida"
    if pd.isna(mes):
        return "Sin mes"
    return "Seca" if int(mes) in MESES_SECOS[n] else "Resto"


# 1. Carga ---------------------------------------------------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
df = df[
    df["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
].copy()
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df = df[df["area_total"] > 0].copy()
print(f"Registros con área positiva: {len(df)}  (control: 41746)")

df["region"] = df["departamento"].map(region_de)
sin_region = df.loc[df["region"] == "SIN REGION", "departamento"].value_counts()
if len(sin_region):
    print("\nAVISO: departamentos sin región (agrégalos a REGIONES):")
    print(sin_region.to_string())

# 2. Fase ENSO ------------------------------------------------------------------
oni = pd.read_csv(RES / "serie_mensual_con_ONI.csv")
oni = oni[["anio", "mes", "fase_episodio"]].drop_duplicates(["anio", "mes"]).copy()
oni["t"] = pd.to_numeric(oni["anio"], errors="coerce") * 12 + pd.to_numeric(oni["mes"], errors="coerce") - 1
oni = oni[["t", "fase_episodio"]].drop_duplicates("t")

df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
df["t"] = df["anio"] * 12 + df["mes"] - 1 - REZAGO_FASE
df = df.merge(oni, on="t", how="left")
df["fase_episodio"] = df["fase_episodio"].fillna("Sin fase")
df.loc[df["anio"] > ANIO_MAX_ENSO, "fase_episodio"] = "Sin fase"
print("\nRegistros por fase ENSO:")
print(df["fase_episodio"].value_counts().to_string())
print("(control con REZAGO_FASE = 0: El Nino 17698, Neutral 15171, La Nina 5617, Sin fase 3260)")

# 3. Estación -------------------------------------------------------------------
df["estacion"] = [estacion_de(d, m) for d, m in zip(df["departamento"], df["mes"])]
print("\nRegistros por estación:")
print(df["estacion"].value_counts().to_string())
print("Suma de las categorías:", len(df), "(debe ser igual a los registros con área positiva)")
sd = df[df["estacion"] == "Sin estación definida"]
print("Sin estación definida: Amazonas y San Andrés = %d (control: 96)" % len(sd))


# 4. Resumen por región y fase ---------------------------------------------------
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
            txt.loc[r, c] = "-" if pd.isna(v) else f"{v:,.1f}{'*' if k < MIN_N else ''}"
    print(f"\n{titulo}")
    print(txt.to_string())


sufijo = "" if REZAGO_FASE == 0 else f"_rezago{REZAGO_FASE}"
for est, archivo in [("Seca", "seca"), ("Resto", "resto")]:
    t = tabla(df[df["estacion"] == est])
    t.to_csv(RES / f"tamanos_region_ENSO_estacion_{archivo}{sufijo}.csv", index=False, encoding="utf-8-sig")
    print("\n" + "=" * 60)
    print(f"ESTACIÓN: {est.upper()} (según los meses secos de cada departamento)")
    mostrar(t, "n", "Número de registros (n):")
    mostrar(t, "mediana", "Mediana de area_total (hectáreas):")
    mostrar(t, "p90", "Percentil 90 de area_total (hectáreas):")
print(f"\n* = menos de {MIN_N} registros en la celda: no es confiable.")
print("Control Orinoquía, estación seca (debe ser MENOR que con dic-mar para todos: 1887 El Nino, 988 La Nina, 1058 Neutral; Meta pierde marzo).")
print(f"\nGuardado: tamanos_region_ENSO_estacion_seca{sufijo}.csv y tamanos_region_ENSO_estacion_resto{sufijo}.csv")
