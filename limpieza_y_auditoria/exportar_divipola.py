"""
Exporta los códigos DANE (DIVIPOLA) de la capa municipal MGN 2025 y arma una tabla
de equivalencias entre los nombres de la base del IDEAM y los códigos DANE.

Salidas (en resultados/):
  - divipola_municipios_dane2025.csv   (un municipio por fila, con sus códigos y área en km2)
  - equivalencia_base_dane.csv         (cada par departamento-municipio de la base y su código)

Los códigos se guardan como TEXTO para no perder los ceros a la izquierda
(por ejemplo "05001" y no "5001").

Requiere en la misma carpeta:
  - limites_dane/ (capa municipal MGN, archivo .shp con "MPIO")
  - nombres_sin_cruce.csv (con la columna equivalente_DANE)
  - resultados/incendios_consolidados_auditados.csv
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path(__file__).resolve().parent
LIMITES = BASE / "limites_dane"
EQUIV = BASE / "nombres_sin_cruce.csv"
CONSOLIDADO = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA_1 = BASE / "resultados" / "divipola_municipios_dane2025.csv"
SALIDA_2 = BASE / "resultados" / "equivalencia_base_dane.csv"


def norm(texto):
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.upper()).strip()


# --- Capa municipal ---
shps = sorted(p for p in LIMITES.rglob("*.shp") if "MPIO" in str(p).upper())
if not shps:
    raise SystemExit("No encontre ningun .shp municipal dentro de limites_dane/")
print("Capa municipal usada:", shps[0].relative_to(BASE))
muni = pd.DataFrame(gpd.read_file(shps[0]).drop(columns="geometry"))
print("Columnas de la capa:", list(muni.columns))

col_dpto_cod = next(c for c in muni.columns if c.lower() == "dpto_ccdgo")
col_dpto_nom = next(c for c in muni.columns if c.lower() == "dpto_cnmbr")
col_mpio_nom = next(c for c in muni.columns if c.lower() == "mpio_cnmbr")
col_area = next(c for c in muni.columns if "narea" in c.lower())
col_mpio_cod = next((c for c in muni.columns if c.lower() == "mpio_cdpmp"), None)
if col_mpio_cod is None:
    col_mpio_ccdgo = next(c for c in muni.columns if c.lower() == "mpio_ccdgo")
    muni["mpio_cdpmp_calc"] = (muni[col_dpto_cod].astype(str).str.zfill(2)
                               + muni[col_mpio_ccdgo].astype(str).str.zfill(3))
    col_mpio_cod = "mpio_cdpmp_calc"

out1 = pd.DataFrame({
    "codigo_dpto": muni[col_dpto_cod].astype(str).str.zfill(2),
    "nombre_dpto": muni[col_dpto_nom],
    "codigo_mpio": muni[col_mpio_cod].astype(str).str.zfill(5),
    "nombre_mpio": muni[col_mpio_nom],
    "area_km2": muni[col_area].round(3),
}).sort_values("codigo_mpio")
SALIDA_1.parent.mkdir(exist_ok=True)
out1.to_csv(SALIDA_1, index=False, encoding="utf-8-sig")
print("\n[1] Municipios:", len(out1),
      "| departamentos:", out1["codigo_dpto"].nunique(),
      "| codigos municipio repetidos:", int(out1["codigo_mpio"].duplicated().sum()),
      "| largo de codigo (debe ser 5):", sorted(out1["codigo_mpio"].str.len().unique()))

# --- Equivalencias con los nombres de la base ---
eq = pd.read_csv(EQUIV, encoding="utf-8-sig", dtype=str).fillna("")
eq = eq[eq["equivalente_DANE"].str.strip() != ""]
EQ = {(norm(r.departamento), norm(r.municipio)): norm(r.equivalente_DANE)
      for r in eq.itertuples()}
EQ = {("BOGOTA, D.C." if d.startswith("BOGOTA") else d, m): v for (d, m), v in EQ.items()}


def clave(dpto, mpio):
    d, m = norm(dpto), norm(mpio)
    if d.startswith("BOGOTA") or m.startswith("BOGOTA"):
        d, m = "BOGOTA, D.C.", "BOGOTA, D.C."
    return d + "|" + EQ.get((d, m), m)


out1["k"] = [clave(d, m) for d, m in zip(out1["nombre_dpto"], out1["nombre_mpio"])]
dane = out1.drop_duplicates("k")[["k", "codigo_mpio", "nombre_mpio"]]

c = pd.read_csv(CONSOLIDADO, low_memory=False)
c = c[c["usar_principal"].astype(str).str.lower().isin(["true", "1"])].copy()
c["k"] = [clave(d, m) for d, m in zip(c["departamento"], c["municipio"])]
par = (c.groupby(["k", "departamento", "municipio"], dropna=False, as_index=False)
         .size().rename(columns={"size": "registros"}))
par = par.merge(dane, on="k", how="left").rename(columns={"nombre_mpio": "nombre_dane"})
par["con_codigo"] = par["codigo_mpio"].notna()
par = par.sort_values(["con_codigo", "registros"], ascending=[True, False])
par.drop(columns="k").to_csv(SALIDA_2, index=False, encoding="utf-8-sig")

sin = par[~par["con_codigo"]]
print("\n[2] Registros del principal:", len(c))
print("[2] Pares departamento-municipio en la base:", len(par),
      "| sin codigo:", len(sin), "| registros sin codigo:", int(sin["registros"].sum()))
print(sin[["departamento", "municipio", "registros"]].head(15).to_string(index=False))
print("\nGuardados:", SALIDA_1.name, "y", SALIDA_2.name)
