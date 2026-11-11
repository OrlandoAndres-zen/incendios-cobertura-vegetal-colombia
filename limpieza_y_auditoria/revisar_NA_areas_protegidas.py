"""
revisar_NA_areas_protegidas.py  (G-07, pendiente del valor "NA")

Pandas lee el texto "NA" (y otros como "N/A", "NULL", "None") como celda vacia.
Este script lee el CSV sin esa conversion y cuenta, en el escenario principal,
cuantos registros tienen cada uno de esos textos en area_protegida.
NO cambia ningun dato: solo cuenta.

Uso (dentro de entrega_incendios, con el .venv activo):
    python revisar_NA_areas_protegidas.py
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"

# Textos que pandas convierte en vacio si no se le pide lo contrario
TEXTOS_NA = ["", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
             "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None",
             "n/a", "nan", "null"]

df = pd.read_csv(CSV, low_memory=False, keep_default_na=False, dtype=str)
print("Filas del CSV:", len(df), "(control: 47.527)")
df = df[df["usar_principal"].str.strip().str.lower().isin(["true", "1", "1.0", "si", "sí"])].copy()
print("Escenario principal:", len(df), "(control: 45.166)")

v = df["area_protegida"].str.strip()
print("\nTextos que pandas habria tomado como vacio (conteo exacto):")
cuentas = v[v.isin(TEXTOS_NA)].value_counts()
print(cuentas.rename(lambda x: repr(x)).to_string())

es_cero = v == "0"
con_dato = ~v.isin(TEXTOS_NA) & ~es_cero
print("\nCon area_protegida escrita (sin vacios, NA ni 0):", int(con_dato.sum()), "(control: 881)")
print("Con area_protegida igual a '0':", int(es_cero.sum()))
print("Cuantos mas aparecen si se cuenta 'NA' como dato:", int((v == "NA").sum()))

# Que hay en las filas donde area_protegida es "NA": ¿trae algo en otras columnas?
na = df[v == "NA"]
print("\nFilas con area_protegida = 'NA':", len(na))
if len(na):
    print("Por anio:")
    print(na["anio"].value_counts().sort_index().to_string())
    print("Por archivo:")
    print(na["archivo"].value_counts().to_string())
