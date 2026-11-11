"""
Análisis de tamaño por departamento (escenario principal).
Colocar en la misma carpeta que analizar_incendios.py y ejecutar con el
entorno virtual activo:  python analisis_tamanos.py

Nota: la unidad de area_total NO está confirmada. No llamarla hectáreas.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"

# 1. Carga y escenario principal -------------------------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
print("Filas totales:", len(df))  # esperado 47527

principal = (
    df["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
)
df = df[principal].copy()
print("Escenario principal:", len(df))  # esperado 45166

df["departamento"] = df["departamento"].fillna("SIN DEPARTAMENTO")
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")

# Solo área positiva para el análisis de tamaño (ceros y faltantes quedan aparte)
pos = df[df["area_total"] > 0].copy()
print("Con área positiva:", len(pos))  # esperado 41746
print("Con área cero:", int((df["area_total"] == 0).sum()))
print("Con área ausente:", int(df["area_total"].isna().sum()))

# 2. Percentiles globales y peso del 1 % mayor -----------------------------
qs = [0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
glob = pos["area_total"].quantile(qs)
print("\nPercentiles globales de area_total:")
print(glob.to_string())

umbral = pos["area_total"].quantile(0.99)
top = pos[pos["area_total"] >= umbral]
share = top["area_total"].sum() / pos["area_total"].sum()
print(f"\nEl 1 % mayor ({len(top)} registros) reúne {share:.1%} de la suma del área")

# 3. Tamaño por departamento ------------------------------------------------
g = pos.groupby("departamento")["area_total"]
por_depto = pd.DataFrame({
    "n_area_positiva": g.size(),
    "mediana": g.median(),
    "p25": g.quantile(0.25),
    "p75": g.quantile(0.75),
    "p90": g.quantile(0.90),
    "p95": g.quantile(0.95),
    "p99": g.quantile(0.99),
    "maximo": g.max(),
    "suma_area": g.sum(),
})
por_depto["iqr"] = por_depto["p75"] - por_depto["p25"]
por_depto = por_depto.sort_values("suma_area", ascending=False)
por_depto.to_csv(RES / "tamanos_por_departamento.csv", encoding="utf-8-sig")
print("\nTamaño por departamento (top 10 por suma de área):")
print(por_depto.head(10).round(1).to_string())

# 4. Ranking: número de registros vs suma de área ---------------------------
conteo = df.groupby("departamento").size().rename("n_registros")
area = pos.groupby("departamento")["area_total"].sum().rename("suma_area")
rank = pd.concat([conteo, area], axis=1).fillna(0)
rank["rango_registros"] = rank["n_registros"].rank(ascending=False, method="min")
rank["rango_area"] = rank["suma_area"].rank(ascending=False, method="min")
rank["diferencia_rangos"] = rank["rango_registros"] - rank["rango_area"]
rank = rank.sort_values("n_registros", ascending=False)
rank.to_csv(RES / "ranking_registros_vs_area.csv", encoding="utf-8-sig")
print("\nRanking registros vs área (top 10 por registros):")
print(rank.head(10).round(1).to_string())

# 5. Curva de excedencia (escala log-log, solo descriptiva) ----------------
vals = np.sort(pos["area_total"].to_numpy())
exced = 1 - np.arange(len(vals)) / len(vals)  # P(X >= x)
fig, ax = plt.subplots(figsize=(7, 5))
ax.loglog(vals, exced, ".", markersize=3)
ax.set_xlabel("area_total (unidad original sin confirmar)")
ax.set_ylabel("Proporción de eventos con área ≥ x")
ax.set_title("Curva de excedencia del tamaño (escenario principal)")
ax.grid(True, which="both", alpha=0.3)
fig.tight_layout()
fig.savefig(RES / "curva_excedencia.png", dpi=150)
print("\nGuardado: tamanos_por_departamento.csv, ranking_registros_vs_area.csv, curva_excedencia.png")
