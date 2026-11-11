"""
Sensibilidad ampliada del análisis de tamaño (versión corregida).
Compara cinco escenarios, todos con area_total > 0:
  A: escenario principal completo
  B: sin repeticiones exactas DENTRO del escenario principal (se conserva la primera copia)
  C: sin 2024
  D: sin 2024 ni 2025
  E: sin repeticiones y sin 2024 ni 2025

Corrección respecto a la versión anterior: ya no se usa la columna
duplicado_exacto_posterior, porque marca como "posteriores" las filas de 2010
cuya primera copia está en otro archivo y fuera del escenario principal. Aquí
las repeticiones se recalculan solo dentro del escenario principal.

Ejecutar desde entrega_incendios/ con el entorno activo:
    python sensibilidad_ampliada_v2.py

No se borra nada de los datos: solo se calculan resultados.
area_total está en hectáreas (IDEAM, radicado 20265000183351).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
VERDADEROS = ["true", "1", "1.0", "si", "sí"]
# Columnas que NO cuentan para decidir si dos filas son la misma
NO_CONTENIDO = {"archivo", "hoja", "fila_excel", "usar_principal",
                "duplicado_exacto_candidato", "duplicado_exacto_posterior"}


def bandera(serie):
    return serie.astype(str).str.strip().str.lower().isin(VERDADEROS)


# 1. Escenario principal y repeticiones exactas dentro de él ----------------------
d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
principal = d[bandera(d["usar_principal"])].copy()
print(f"Escenario principal: {len(principal)}")  # esperado 45166

columnas = [c for c in principal.columns if c not in NO_CONTENIDO]
principal["_repetida"] = principal.duplicated(subset=columnas, keep="first")
print(f"Repeticiones exactas dentro del principal (recalculadas): {int(principal['_repetida'].sum())}")
print("  (el resumen de auditoría dice 773)")

# 2. Área positiva -----------------------------------------------------------------------
principal["area_total"] = pd.to_numeric(principal["area_total"], errors="coerce")
df = principal[principal["area_total"] > 0].copy()
df["departamento"] = df["departamento"].fillna("SIN DEPARTAMENTO")
df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
print(f"Registros con área positiva: {len(df)}")  # esperado 41746
print(f"  de ellos, repeticiones exactas: {int(df['_repetida'].sum())}")

por_anio = df.groupby("anio").size()
print("\nRegistros con área positiva por año reciente:")
print(por_anio.loc[por_anio.index >= 2019].astype(int).to_string())

# 3. Escenarios -------------------------------------------------------------------------
es_rep = df["_repetida"]
recientes = df["anio"].isin([2024, 2025])
escenarios = {
    "A_todos": df,
    "B_sin_repeticiones": df[~es_rep],
    "C_sin_2024": df[df["anio"] != 2024],
    "D_sin_2024_2025": df[~recientes],
    "E_sin_rep_ni_2024_25": df[~es_rep & ~recientes],
}


def resumen(s):
    a = s["area_total"]
    umbral = a.quantile(0.99)
    return {
        "n_registros": len(a),
        "mediana": a.median(),
        "p75": a.quantile(0.75),
        "p90": a.quantile(0.90),
        "p95": a.quantile(0.95),
        "p99": a.quantile(0.99),
        "maximo": a.max(),
        "suma_area": a.sum(),
        "pct_area_del_1pct_mayor": 100 * a[a >= umbral].sum() / a.sum(),
    }


tabla = pd.DataFrame({k: resumen(v) for k, v in escenarios.items()}).T
tabla.to_csv(RES / "sensibilidad_ampliada_v2_global.csv", encoding="utf-8-sig")
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)
print("\nPercentiles por escenario:")
print(tabla.round(1).to_string())

cambio = (100 * (tabla / tabla.loc["A_todos"] - 1)).drop(index="A_todos")
print("\nCambio % respecto a A:")
print(cambio.round(1).to_string())

# 4. Ranking de departamentos por área: A contra E ------------------------------------
suma = pd.DataFrame({k: v.groupby("departamento")["area_total"].sum() for k, v in escenarios.items()}).fillna(0)
rangos = suma.rank(ascending=False, method="min").add_prefix("rango_")
rank = pd.concat([suma.add_prefix("suma_"), rangos], axis=1).sort_values("suma_A_todos", ascending=False)
rank.to_csv(RES / "sensibilidad_ampliada_v2_departamentos.csv", encoding="utf-8-sig")
vista = rank[["suma_A_todos", "suma_E_sin_rep_ni_2024_25", "rango_A_todos", "rango_E_sin_rep_ni_2024_25"]].head(10)
vista.columns = ["suma_A", "suma_E", "rango_A", "rango_E"]
vista["cambio_pct"] = 100 * (vista["suma_E"] / vista["suma_A"] - 1)
print("\nRanking por área, A contra E (top 10 de A):")
print(vista.round(1).to_string())

# 5. Curvas de excedencia: A contra E ----------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 5))
for nombre, datos, color, tam in [
    ("A: todos", escenarios["A_todos"], "tab:blue", 6),
    ("E: sin repeticiones ni 2024-2025", escenarios["E_sin_rep_ni_2024_25"], "tab:orange", 3),
]:
    v = np.sort(datos["area_total"].to_numpy())
    ax.loglog(v, 1 - np.arange(len(v)) / len(v), ".", markersize=tam, color=color, label=nombre)
ax.set_xlabel("area_total (hectáreas)")
ax.set_ylabel("Proporción de eventos con área ≥ x")
ax.set_title("Sensibilidad ampliada de la curva de excedencia")
ax.grid(True, which="both", alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(RES / "sensibilidad_ampliada_v2_curva.png", dpi=150)

print("\nGuardado: sensibilidad_ampliada_v2_global.csv, sensibilidad_ampliada_v2_departamentos.csv, sensibilidad_ampliada_v2_curva.png")
