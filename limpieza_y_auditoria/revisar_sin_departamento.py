"""
Revisa los registros del escenario principal que no tienen departamento
(los que no entran en los mapas por departamento).

Ejecutar desde entrega_incendios/ con el entorno activo:
    python revisar_sin_departamento.py
"""
from pathlib import Path

import pandas as pd

RES = Path(__file__).resolve().parent / "resultados"

d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
p = d[
    d["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
]
sin = p[p["departamento"].isna()].copy()

print(f"Registros del escenario principal: {len(p)}")  # esperado 45166
print(f"Sin departamento: {len(sin)}")  # esperado 108

area = pd.to_numeric(sin["area_total"], errors="coerce")
print(f"  con área positiva: {int((area > 0).sum())}")
print(f"  con área cero: {int((area == 0).sum())}")
print(f"  con área ausente: {int(area.isna().sum())}")

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)

if len(sin):
    print("\nCómo venía escrito el departamento en el original:")
    print(sin["departamento_original"].value_counts(dropna=False).head(10).to_string())

    print("\nPor archivo:")
    print(sin["archivo"].value_counts().to_string())

    print("\nPor año:")
    print(sin["anio"].value_counts().sort_index().to_string())

    cols = [c for c in ["anio", "municipio", "municipio_original", "area_total",
                        "archivo", "fila_excel"] if c in sin.columns]
    print("\nPrimeros 10:")
    print(sin[cols].head(10).to_string(index=False))
