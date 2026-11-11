"""
Lista los registros del escenario principal cuyo municipio no se pudo cruzar con el DANE:
  - los pares departamento-municipio sin equivalente_DANE en nombres_sin_cruce.csv
  - los registros de AMAZONAS sin municipio
Muestra vereda, predio, área, archivo, hoja y fila del Excel para poder decidir cada caso.
Guarda el resultado en resultados/revision_sin_cruce.csv

Requiere en la misma carpeta:
  - nombres_sin_cruce.csv
  - resultados/incendios_consolidados_auditados.csv
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
EQUIV = BASE / "nombres_sin_cruce.csv"
CONSOLIDADO = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = BASE / "resultados" / "revision_sin_cruce.csv"


def norm(x):
    if pd.isna(x):
        return ""
    t = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.upper()).strip()


eq = pd.read_csv(EQUIV, encoding="utf-8-sig", dtype=str).fillna("")
pend = eq[eq["equivalente_DANE"].str.strip() == ""]
pares = {(norm(r.departamento), norm(r.municipio)) for r in pend.itertuples()}
print("Pares sin equivalencia en el archivo:", len(pares))

c = pd.read_csv(CONSOLIDADO, low_memory=False)
c = c[c["usar_principal"].astype(str).str.lower().isin(["true", "1"])].copy()
c["d"] = c["departamento"].map(norm)
c["m"] = c["municipio"].map(norm)

es_par = [(d, m) in pares for d, m in zip(c["d"], c["m"])]
es_amazonas = (c["d"] == "AMAZONAS") & (c["m"] == "")
sel = c[es_par | es_amazonas].copy()
sel["grupo"] = ["Amazonas sin municipio" if a else "Nombre pendiente"
                for a in es_amazonas[es_par | es_amazonas]]

cols = ["grupo", "anio", "fecha", "departamento", "municipio", "vereda", "predio",
        "area_total", "archivo", "hoja", "fila_excel"]
cols = [x for x in cols if x in sel.columns]
sel = sel.sort_values(["grupo", "departamento", "municipio", "anio"])[cols]

print("\nRegistros encontrados:", len(sel))
print(sel.groupby(["grupo", "departamento", "municipio"], dropna=False).size().to_string())
print()
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 40)
print(sel.drop(columns=["archivo"]).to_string(index=False))

SALIDA.parent.mkdir(exist_ok=True)
sel.to_csv(SALIDA, index=False, encoding="utf-8-sig")
print("\nGuardado en:", SALIDA.relative_to(BASE))
