"""
Versión 2. Hace dos comparaciones con la superficie oficial del municipio (DANE MGN):
  A) Los 30 mayores registros (M-01 a M-30), uno por uno.
  B) Todos los registros del escenario principal, sumados por municipio y año.
No cambia ninguna decisión: solo marca los casos que requieren revisión.

Requiere en la misma carpeta:
  - tabla_decisiones_limpieza.xlsx
  - resultados/incendios_consolidados_auditados.csv
  - limites_dane/ (con la capa municipal MGN, archivo .shp con "MPIO")
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent
TABLA = BASE / "tabla_decisiones_limpieza.xlsx"
CONSOLIDADO = BASE / "resultados" / "incendios_consolidados_auditados.csv"
LIMITES = BASE / "limites_dane"
SALIDA_A = BASE / "resultados" / "comparacion_municipios_30.csv"
SALIDA_B = BASE / "resultados" / "comparacion_municipio_anio.csv"


def norm(texto):
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.upper()).strip()


# --- Capa municipal del DANE ---
shps = sorted(p for p in LIMITES.rglob("*.shp") if "MPIO" in str(p).upper())
if not shps:
    raise SystemExit("No encontre ningun .shp municipal dentro de limites_dane/")
print("Capa municipal usada:", shps[0].relative_to(BASE))
muni = gpd.read_file(shps[0])
col_area = next(c for c in muni.columns if "narea" in c.lower())
print("Campo de area:", col_area, "(se asume km2)")
muni["k"] = muni["dpto_cnmbr"].map(norm) + "|" + muni["mpio_cnmbr"].map(norm)
muni = muni[["k", col_area]].rename(columns={col_area: "muni_km2"})

# --- A) Los 30 mayores ---
ws = load_workbook(TABLA, read_only=True)["Decisiones"]
enc = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
filas = [dict(zip(enc, r)) for r in ws.iter_rows(min_row=2, values_only=True)
         if r[0] and str(r[0]).startswith("M-")]
a = pd.DataFrame(filas)[["id", "anio", "departamento", "municipio", "area_total"]]
a["area_total"] = pd.to_numeric(a["area_total"], errors="coerce")
a["k"] = a["departamento"].map(norm) + "|" + a["municipio"].map(norm)
a = a.merge(muni, on="k", how="left")
print("\n[A] Registros M leidos:", len(a), "| sin coincidencia:", a["muni_km2"].isna().sum())
a["pct_si_ha"] = (a["area_total"] / 100 / a["muni_km2"] * 100).round(2)
a = a.sort_values("pct_si_ha", ascending=False)
print("[A] Superan el municipio (si la unidad es ha):", int((a["pct_si_ha"] > 100).sum()))
a.drop(columns="k").to_csv(SALIDA_A, index=False, encoding="utf-8")

# --- B) Todos los registros, sumados por municipio y año ---
c = pd.read_csv(CONSOLIDADO, low_memory=False)
c = c[c["usar_principal"].astype(str).str.lower().isin(["true", "1"])]
c["area_total"] = pd.to_numeric(c["area_total"], errors="coerce")
c = c[c["area_total"] > 0]
print("\n[B] Registros del principal con area > 0:", len(c))
c["k"] = c["departamento"].map(norm) + "|" + c["municipio"].map(norm)
b = (c.groupby(["k", "departamento", "municipio", "anio"], as_index=False)
       .agg(n_registros=("area_total", "size"), suma_area=("area_total", "sum")))
b = b.merge(muni, on="k", how="left")
print("[B] Municipio-año sin coincidencia en la capa:", b["muni_km2"].isna().sum())
b["pct_si_ha"] = (b["suma_area"] / 100 / b["muni_km2"] * 100).round(2)
b = b.sort_values("pct_si_ha", ascending=False)
print("[B] Municipio-año que superan el municipio (si la unidad es ha):",
      int((b["pct_si_ha"] > 100).sum()))
print(b[["anio", "municipio", "n_registros", "suma_area", "muni_km2", "pct_si_ha"]]
      .head(15).to_string(index=False))
b.drop(columns="k").to_csv(SALIDA_B, index=False, encoding="utf-8")
print("\nGuardados:", SALIDA_A.name, "y", SALIDA_B.name)
