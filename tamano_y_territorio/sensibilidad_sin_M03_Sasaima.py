"""
sensibilidad_sin_M03_Sasaima.py

Repite el analisis de tamano (area_total > 0, escenario principal) en tres escenarios:
  A: todos (41.746 registros)
  F: sin M-03 (Sasaima 2024, 12.000 ha: hoja BD_ICV_2024, fila 6058 del Excel)
  G: sin Sasaima 2024 (los 15 registros de ese municipio y anio; incluye M-03)

Solo calcula: no borra ni cambia nada en los datos.
area_total esta en hectareas (IDEAM, radicado 20265000183351).

Uso (dentro de entrega_incendios, con el .venv activo):
    python sensibilidad_sin_M03_Sasaima.py
"""
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
VERDADEROS = ["true", "1", "1.0", "si", "sí"]


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


# 1. Escenario principal con area positiva ---------------------------------------
d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
d = d[d["usar_principal"].astype(str).str.strip().str.lower().isin(VERDADEROS)].copy()
print("Escenario principal:", len(d), "(control: 45.166)")
d["area_total"] = pd.to_numeric(d["area_total"], errors="coerce")
df = d[d["area_total"] > 0].copy()
print("Registros con area positiva:", len(df), "(control: 41.746)")

df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
df["departamento"] = df["departamento"].fillna("SIN DEPARTAMENTO")
df["_mpio"] = df["municipio"].map(normalizar)
df["_hoja"] = df["hoja"].astype(str).str.strip()
df["_fila"] = pd.to_numeric(df["fila_excel"], errors="coerce")

# 2. Identificar los registros a quitar -------------------------------------------
es_sasaima = (df["_mpio"] == "SASAIMA") & (df["anio"] == 2024)
es_m03 = (df["_hoja"] == "BD_ICV_2024") & (df["_fila"] == 6058) & es_sasaima

print("\nFormas de escribir el municipio que se tomaron como Sasaima 2024:")
print(df.loc[es_sasaima, ["departamento", "municipio"]].value_counts().to_string())
print("\nSasaima 2024: %d registros, %.1f ha  (control: 15 registros, 15.022,5 ha)"
      % (es_sasaima.sum(), df.loc[es_sasaima, "area_total"].sum()))
print("M-03: %d registro, %.1f ha  (control: 1 registro, 12.000,0 ha)"
      % (es_m03.sum(), df.loc[es_m03, "area_total"].sum()))
if es_sasaima.sum() != 15 or es_m03.sum() != 1:
    print("ATENCION: las cifras de arriba no coinciden con el control. Mandame esta salida.")

escenarios = {
    "A_todos": df,
    "F_sin_M03": df[~es_m03],
    "G_sin_Sasaima_2024": df[~es_sasaima],
}


# 3. Resumen global ------------------------------------------------------------------
def resumen(s):
    a = s["area_total"]
    u = a.quantile(0.99)
    return {
        "n_registros": len(a),
        "mediana": a.median(),
        "p75": a.quantile(0.75),
        "p90": a.quantile(0.90),
        "p95": a.quantile(0.95),
        "p99": a.quantile(0.99),
        "maximo": a.max(),
        "suma_area_ha": a.sum(),
        "pct_area_del_1pct_mayor": 100 * a[a >= u].sum() / a.sum(),
    }


tabla = pd.DataFrame({k: resumen(v) for k, v in escenarios.items()}).T
tabla.to_csv(RES / "sensibilidad_sin_M03_Sasaima_global.csv", encoding="utf-8-sig")
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)
print("\nResumen por escenario (hectareas):")
print(tabla.round(1).to_string())
print("\nCambio % respecto a A:")
print((100 * (tabla / tabla.loc["A_todos"] - 1)).drop(index="A_todos").round(1).to_string())

# 4. Ranking de departamentos por area --------------------------------------------
suma = pd.DataFrame({k: v.groupby("departamento")["area_total"].sum() for k, v in escenarios.items()}).fillna(0)
rangos = suma.rank(ascending=False, method="min").add_prefix("rango_")
rank = pd.concat([suma.add_prefix("suma_"), rangos], axis=1).sort_values("suma_A_todos", ascending=False)
rank.to_csv(RES / "sensibilidad_sin_M03_Sasaima_departamentos.csv", encoding="utf-8-sig")
print("\nRanking por area (top 10 de A):")
print(rank.head(10).round(1).to_string())
print("\nGuardado: sensibilidad_sin_M03_Sasaima_global.csv y sensibilidad_sin_M03_Sasaima_departamentos.csv")
