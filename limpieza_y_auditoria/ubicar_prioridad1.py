"""
ubicar_prioridad1.py

Ubica los 4 registros de prioridad 1 para revisarlos a mano en los Excel originales:
  Palmira (Valle) 2024, 30.000
  Palermo (Huila) 2024, 13.290
  Sasaima (Cundinamarca) 2024, 12.000
  Arauquita (Arauca) 2010, 10.000

Muestra archivo, hoja y fila de Excel de cada uno, y lo que dice la base.
Incluye tambien copias que existan en otro archivo (no solo el escenario principal).

Uso (dentro de entrega_incendios, con el .venv activo):
    python ubicar_prioridad1.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = BASE / "resultados" / "ubicacion_prioridad1.csv"

OBJETIVOS = [
    ("PALMIRA", 2024, 30000.0),
    ("PALERMO", 2024, 13290.0),
    ("SASAIMA", 2024, 12000.0),
    ("ARAUQUITA", 2010, 10000.0),
]
COLUMNAS = [
    "archivo", "hoja", "fila_excel", "usar_principal", "anio", "mes_original",
    "departamento", "municipio", "vereda", "predio", "area_total_original",
    "area_total", "duplicado_exacto_candidato", "duplicado_exacto_posterior",
]


def clave(texto):
    if pd.isna(texto):
        return ""
    t = unicodedata.normalize("NFKD", str(texto).upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^A-Z]", "", t)


df = pd.read_csv(CSV, low_memory=False)
print("Filas del CSV:", len(df), "(control: 47.527)")
df["_mun"] = df["municipio"].map(clave)
df["_area"] = pd.to_numeric(df["area_total"], errors="coerce")
df["_anio"] = pd.to_numeric(df["anio"], errors="coerce")

cols = [c for c in COLUMNAS if c in df.columns]
partes = []
for mun, anio, area in OBJETIVOS:
    sel = df[(df["_mun"] == mun) & (df["_anio"] == anio) & ((df["_area"] - area).abs() < 0.01)]
    print("\n=== %s %d, area %s: %d fila(s) encontrada(s) ===" % (mun, anio, int(area), len(sel)))
    if len(sel):
        print(sel[cols].to_string(index=False))
        partes.append(sel[cols])

if partes:
    pd.concat(partes).to_csv(SALIDA, index=False, encoding="utf-8")
    print("\nGuardado en:", SALIDA)
