"""
densidad_departamentos.py  (Paso 2)

Calcula, por departamento:
  - registros del escenario principal
  - suma de area_total positiva (hectareas; IDEAM, radicado 20265000183351)
  - registros por 1.000 km2
  - hectareas por km2

Superficie: columna dpto_narea del DANE MGN 2025 (km2; metadatos del DANE: 'Area departamento (Km2)').

Uso (dentro de entrega_incendios, con el .venv activo):
    python densidad_departamentos.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
import shapefile  # pyshp

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SHP = BASE / "limites_dane" / "MGN2025_DPTO_POLITICO" / "MGN_ADM_DPTO_POLITICO.shp"
SALIDA = BASE / "resultados" / "densidad_departamental.csv"


def clave(texto):
    """Nombre en mayusculas, sin tildes ni signos, para poder unir tablas."""
    if pd.isna(texto):
        return ""
    t = str(texto).upper()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Z]", "", t)
    if "BOGOTA" in t:
        return "BOGOTA"
    if "SANANDRES" in t:
        return "SANANDRES"
    return t


# ---------- 1. Incendios (IDEAM) ----------
df = pd.read_csv(CSV, low_memory=False)
print("Filas del CSV:", len(df), "(control: 47.527)")

principal = df["usar_principal"].astype(str).str.lower().isin(["true", "1"])
df = df[principal].copy()
print("Escenario principal:", len(df), "(control: 45.166)")

df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df["clave"] = df["departamento"].map(clave)

sin_dep = (df["clave"] == "").sum()
print("Sin departamento:", sin_dep, "(esperado: 108)")

con_dep = df[df["clave"] != ""]
registros = con_dep.groupby("clave").size().rename("registros")
pos = con_dep[con_dep["area_total"] > 0]
area = pos.groupby("clave")["area_total"].agg(
    registros_area_positiva="size", area_suma_ha="sum"
)
tabla_inc = pd.concat([registros, area], axis=1).reset_index()

# ---------- 2. Limites (DANE) ----------
try:
    sf = shapefile.Reader(str(SHP), encoding="utf-8", encodingErrors="replace")
except TypeError:
    sf = shapefile.Reader(str(SHP), encoding="utf-8")
campos = [f[0] for f in sf.fields[1:]]


def buscar(parte):
    for i, c in enumerate(campos):
        if parte in c.lower():
            return i
    raise SystemExit("No encontre el campo que contiene '" + parte + "'. Campos: " + str(campos))


i_cod, i_nom, i_area = buscar("ccdgo"), buscar("cnmbr"), buscar("narea")
filas = []
for r in sf.records():
    filas.append(
        {
            "codigo_dane": str(r[i_cod]).zfill(2),
            "departamento": str(r[i_nom]),
            "km2_dane": float(r[i_area]),
        }
    )
dane = pd.DataFrame(filas)
dane["clave"] = dane["departamento"].map(clave)
print("Departamentos DANE:", len(dane), "(esperado: 33)")

# ---------- 3. Union y calculo ----------
out = dane.merge(tabla_inc, on="clave", how="outer", indicator=True)

no_union = out[out["_merge"] != "both"]
if len(no_union):
    print("\nATENCION: nombres que no se unieron:")
    print(no_union[["clave", "codigo_dane", "registros"]].to_string(index=False))
else:
    print("Todos los nombres se unieron bien.")

out = out[out["_merge"] == "both"].drop(columns=["_merge", "clave"])
out["registros_por_1000km2"] = out["registros"] / out["km2_dane"] * 1000
out["hectareas_por_km2"] = out["area_suma_ha"] / out["km2_dane"]
out = out.sort_values("registros_por_1000km2", ascending=False)
out.to_csv(SALIDA, index=False, encoding="utf-8")

# ---------- 4. Cifras de control ----------
print("\nSuma de registros en la tabla:", int(out["registros"].sum()), "(esperado: 45.058)")
print("Registros con area positiva:", int(out["registros_area_positiva"].sum()), "(esperado: 41.746)")
print("Suma de area (hectareas):", round(out["area_suma_ha"].sum(), 1), "(esperado: 2.163.299,3)")
print("\nTop 5 por registros por 1.000 km2:")
print(out[["departamento", "registros", "km2_dane", "registros_por_1000km2"]].head(5).round(2).to_string(index=False))
print("\nTop 5 por hectareas por km2:")
print(out.sort_values("hectareas_por_km2", ascending=False)[["departamento", "area_suma_ha", "km2_dane", "hectareas_por_km2"]].head(5).round(2).to_string(index=False))
print("\nGuardado en:", SALIDA)
