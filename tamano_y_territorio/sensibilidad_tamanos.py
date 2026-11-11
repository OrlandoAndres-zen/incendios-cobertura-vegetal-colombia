"""
Sensibilidad del análisis de tamaño.
Compara tres escenarios para ver si las conclusiones dependen de los
registros que quedaron marcados para revisión:
  A: todo el escenario principal con área positiva
  B: A sin los 4 registros de prioridad 1
  C: A sin los 15 registros de prioridad 1 y 2

Ejecutar desde entrega_incendios/ con el entorno activo:
    python sensibilidad_tamanos.py

No se borra ni corrige nada en los datos: solo se calculan resultados.
La unidad de area_total NO está confirmada.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"

# Cada registro se identifica con (archivo, año, fila_excel)
PRIORIDAD_1 = [
    ("2021_2025", 2024, 7058),  # Palmira, Valle
    ("2021_2025", 2024, 6080),  # Palermo, Huila
    ("2021_2025", 2024, 6058),  # Sasaima, Cundinamarca
    ("2010_2020", 2010, 308),   # Arauquita, Arauca (duplicado candidato)
]
PRIORIDAD_2 = [
    ("2002_2010", 2007, 4133),  # La Macarena
    ("2002_2010", 2007, 4134),  # Mapiripán
    ("2002_2010", 2007, 4735),  # Puerto Carreño
    ("2002_2010", 2007, 4736),  # Puerto Carreño
    ("2002_2010", 2007, 4737),  # Puerto Carreño
    ("2010_2020", 2017, 15113),  # Cumaribo
    ("2010_2020", 2017, 15115),  # Cumaribo
    ("2010_2020", 2017, 15133),  # Cumaribo
    ("2010_2020", 2018, 16922),  # Cumaribo
    ("2010_2020", 2018, 16923),  # Cumaribo
    ("2010_2020", 2018, 17089),  # Montería
]


def rango_archivo(nombre):
    for token in ("2002_2010", "2010_2020", "2021_2025"):
        if token in str(nombre):
            return token
    return "otro"


# 1. Carga y escenario principal con área positiva -------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
df = df[
    df["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
].copy()
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df = df[df["area_total"] > 0].copy()
df["departamento"] = df["departamento"].fillna("SIN DEPARTAMENTO")

anio = pd.to_numeric(df["anio"], errors="coerce").fillna(-1).astype(int)
fila = pd.to_numeric(df["fila_excel"], errors="coerce").fillna(-1).astype(int)
df["_clave"] = list(zip(df["archivo"].map(rango_archivo), anio, fila))

es_p1 = df["_clave"].isin(PRIORIDAD_1)
es_p2 = df["_clave"].isin(PRIORIDAD_2)
print(f"Registros con área positiva: {len(df)}")  # esperado 41746
print(f"Prioridad 1 encontrados: {int(es_p1.sum())} de {len(PRIORIDAD_1)}")
print(f"Prioridad 2 encontrados: {int(es_p2.sum())} de {len(PRIORIDAD_2)}")
if es_p1.sum() != len(PRIORIDAD_1) or es_p2.sum() != len(PRIORIDAD_2):
    print("AVISO: no se encontraron todos los registros; revisa los nombres de archivo.")

escenarios = {
    "A_todos": df,
    "B_sin_prioridad1": df[~es_p1],
    "C_sin_prioridad1y2": df[~(es_p1 | es_p2)],
}


# 2. Percentiles globales por escenario ------------------------------------
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
tabla.to_csv(RES / "sensibilidad_global.csv", encoding="utf-8-sig")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
print("\nPercentiles por escenario:")
print(tabla.round(1).to_string())

cambio = 100 * (tabla.loc["C_sin_prioridad1y2"] / tabla.loc["A_todos"] - 1)
print("\nCambio % de C respecto a A:")
print(cambio.round(1).to_string())

# 3. Ranking de departamentos por área: A contra C -------------------------
area_a = escenarios["A_todos"].groupby("departamento")["area_total"].sum()
area_c = escenarios["C_sin_prioridad1y2"].groupby("departamento")["area_total"].sum()
rank = pd.concat([area_a.rename("suma_area_A"), area_c.rename("suma_area_C")], axis=1).fillna(0)
rank["rango_A"] = rank["suma_area_A"].rank(ascending=False, method="min")
rank["rango_C"] = rank["suma_area_C"].rank(ascending=False, method="min")
rank["cambio_rango"] = rank["rango_A"] - rank["rango_C"]
rank["cambio_area_pct"] = 100 * (rank["suma_area_C"] / rank["suma_area_A"] - 1)
rank = rank.sort_values("suma_area_A", ascending=False)
rank.to_csv(RES / "sensibilidad_departamentos.csv", encoding="utf-8-sig")
print("\nRanking por área, A contra C (top 10):")
print(rank.head(10).round(1).to_string())

# 4. Curva de excedencia: A contra C ---------------------------------------
fig, ax = plt.subplots(figsize=(7, 5))
for nombre, datos, color, tam in [
    ("A: todos", escenarios["A_todos"], "tab:blue", 6),
    ("C: sin prioridad 1 y 2", escenarios["C_sin_prioridad1y2"], "tab:orange", 3),
]:
    v = np.sort(datos["area_total"].to_numpy())
    exced = 1 - np.arange(len(v)) / len(v)
    ax.loglog(v, exced, ".", markersize=tam, color=color, label=nombre)
ax.set_xlabel("area_total (unidad original sin confirmar)")
ax.set_ylabel("Proporción de eventos con área ≥ x")
ax.set_title("Sensibilidad de la curva de excedencia")
ax.grid(True, which="both", alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(RES / "sensibilidad_curva.png", dpi=150)

print("\nGuardado: sensibilidad_global.csv, sensibilidad_departamentos.csv, sensibilidad_curva.png")
