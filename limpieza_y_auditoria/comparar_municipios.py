"""
Compara el area_total de los 30 mayores registros (M-01 a M-30) con la
superficie oficial del municipio (DANE MGN). No cambia ninguna decision:
solo marca los casos que requieren revision.

Requiere en la misma carpeta:
  - tabla_decisiones_limpieza.xlsx
  - limites_dane/ (con la capa municipal MGN, archivo .shp)
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent
TABLA = BASE / "tabla_decisiones_limpieza.xlsx"
LIMITES = BASE / "limites_dane"
SALIDA = BASE / "resultados" / "comparacion_municipios_30.csv"


def norm(texto):
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.upper()).strip()


# 1. Leer los M-01 a M-30 de la tabla
ws = load_workbook(TABLA, read_only=True)["Decisiones"]
encabezados = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
filas = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] and str(r[0]).startswith("M-"):
        filas.append(dict(zip(encabezados, r)))
tabla = pd.DataFrame(filas)[["id", "anio", "departamento", "municipio", "area_total"]]
tabla["area_total"] = pd.to_numeric(tabla["area_total"], errors="coerce")
print("Registros M leidos:", len(tabla))

# 2. Encontrar la capa municipal del DANE
shps = sorted(p for p in LIMITES.rglob("*.shp") if "MPIO" in str(p).upper())
if not shps:
    raise SystemExit("No encontre ningun .shp municipal dentro de limites_dane/")
print("Capa municipal usada:", shps[0].relative_to(BASE))
muni = gpd.read_file(shps[0])

col_area = next(c for c in muni.columns if "narea" in c.lower())
print("Campo de area:", col_area, "(se asume km2)")
muni["k"] = muni["dpto_cnmbr"].map(norm) + "|" + muni["mpio_cnmbr"].map(norm)
tabla["k"] = tabla["departamento"].map(norm) + "|" + tabla["municipio"].map(norm)

# 3. Cruzar y calcular
m = tabla.merge(
    muni[["k", col_area]].rename(columns={col_area: "muni_km2"}),
    on="k", how="left",
)
sin = m[m["muni_km2"].isna()]
print("Municipios sin coincidencia:", len(sin))
if len(sin):
    print(sin[["id", "departamento", "municipio"]].to_string(index=False))

# Si la unidad fuera hectareas: 1 km2 = 100 ha
m["si_fuera_ha_km2"] = m["area_total"] / 100
m["pct_municipio_si_ha"] = (m["si_fuera_ha_km2"] / m["muni_km2"] * 100).round(2)
m["supera_si_ha"] = m["pct_municipio_si_ha"] > 100
m = m.sort_values("pct_municipio_si_ha", ascending=False)

print("\nRegistros que superan el municipio entero (si la unidad es ha):",
      int(m["supera_si_ha"].sum()))
print(m[["id", "municipio", "area_total", "muni_km2", "pct_municipio_si_ha"]]
      .head(10).to_string(index=False))

SALIDA.parent.mkdir(exist_ok=True)
m.drop(columns="k").to_csv(SALIDA, index=False, encoding="utf-8")
print("\nGuardado en:", SALIDA.relative_to(BASE))
