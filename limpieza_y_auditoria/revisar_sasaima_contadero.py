"""
Muestra los registros de Sasaima 2024 (Cundinamarca) y Contadero 2019 (Nariño)
del escenario principal, con su archivo, hoja y fila del Excel.
Guarda el resultado en resultados/revision_sasaima_contadero.csv
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = BASE / "resultados" / "revision_sasaima_contadero.csv"


def norm(x):
    if pd.isna(x):
        return ""
    t = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.upper()).strip()


c = pd.read_csv(CSV, low_memory=False)
c = c[c["usar_principal"].astype(str).str.lower().isin(["true", "1"])].copy()
c["area_total"] = pd.to_numeric(c["area_total"], errors="coerce")
c = c[c["area_total"] > 0]
c["m"] = c["municipio"].map(norm)
c["d"] = c["departamento"].map(norm)

casos = {
    "Sasaima 2024": (c["d"] == "CUNDINAMARCA") & (c["m"] == "SASAIMA") & (c["anio"] == 2024),
    "Contadero 2019": (c["d"] == "NARINO") & c["m"].isin(["CONTADERO", "EL CONTADERO"]) & (c["anio"] == 2019),
}

cols = ["anio", "fecha", "departamento", "municipio", "vereda", "predio",
        "area_total", "archivo", "hoja", "fila_excel"]
cols = [x for x in cols if x in c.columns]

salida = []
for nombre, filtro in casos.items():
    sub = c[filtro].sort_values("area_total", ascending=False)
    print(f"\n=== {nombre}: {len(sub)} registros, suma {sub['area_total'].sum():,.1f} ===")
    print(sub[cols].to_string(index=False))
    salida.append(sub[cols].assign(caso=nombre))

pd.concat(salida).to_csv(SALIDA, index=False, encoding="utf-8")
print("\nGuardado en:", SALIDA.relative_to(BASE))
