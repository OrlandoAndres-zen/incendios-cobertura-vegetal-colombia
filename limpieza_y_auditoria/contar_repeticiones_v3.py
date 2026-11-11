"""
contar_repeticiones_v3.py  (G-01 / G-09)

Igual que contar_repeticiones.py, pero con la definicion OFICIAL de repeticion
(acordada por Orlando y Julian): se comparan los mismos campos, con mayusculas,
espacios al inicio/final y espacios dobles unificados. Tambien imprime la cuenta
estricta (textos tal cual) para comparar.

Desglosa las repeticiones del escenario principal (se recalculan solo
dentro del principal, comparando todas las columnas menos archivo, hoja, fila_excel
y las banderas; se conserva la primera copia). Responde:
  - cuantas repeticiones hay en total (control: 773; estricta: 767)
  - cuantas tienen departamento vacio (filas en blanco de G-09)
  - cuantas estan en 2010 y cuantas son del propio 2010
  - cuantas no tienen mes recuperable
  - cuantas tienen area positiva, cero o ausente
Solo cuenta: no cambia ningun dato.

Uso (dentro de entrega_incendios, con el .venv activo):
    python contar_repeticiones_v3.py
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
VERDADEROS = ["true", "1", "1.0", "si", "sí"]
NO_CONTENIDO = {"archivo", "hoja", "fila_excel", "usar_principal",
                "duplicado_exacto_candidato", "duplicado_exacto_posterior"}

d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
p = d[d["usar_principal"].astype(str).str.strip().str.lower().isin(VERDADEROS)].copy()
print("Escenario principal:", len(p), "(control: 45.166)")

columnas = [c for c in p.columns if c not in NO_CONTENIDO]
# Definicion estricta (textos tal cual): solo para comparar
rep_estricta = p.duplicated(subset=columnas, keep="first")
print("Repeticiones ESTRICTAS dentro del principal:", int(rep_estricta.sum()), "(control: 767)")

# Definicion oficial: mayusculas, espacios al inicio/final y espacios dobles unificados
unificado = p[columnas].astype(str).apply(
    lambda s: s.str.replace(r"\s+", " ", regex=True).str.strip().str.lower())
p["_rep"] = unificado.duplicated(keep="first")
print("Repeticiones OFICIALES (unificadas) dentro del principal:", int(p["_rep"].sum()), "(control: 773)")
print("  estricta que no esta en la oficial (debe ser 0):", int((rep_estricta & ~p["_rep"]).sum()))

p["_dep_vacio"] = p["departamento"].isna() | (p["departamento"].astype(str).str.strip() == "")
p["_sin_mes"] = pd.to_numeric(p["mes"], errors="coerce").isna()
p["_anio"] = pd.to_numeric(p["anio"], errors="coerce")
p["_area"] = pd.to_numeric(p["area_total"], errors="coerce")

r = p[p["_rep"]]
print("\nDe las repeticiones:")
print("  con departamento vacio:", int(r["_dep_vacio"].sum()))
print("    de esas, en 2010:", int((r["_dep_vacio"] & (r["_anio"] == 2010)).sum()))
print("  con departamento y SIN mes recuperable:", int((~r["_dep_vacio"] & r["_sin_mes"]).sum()))
print("  con departamento y con mes (lo que ve un panel departamento x mes):",
      int((~r["_dep_vacio"] & ~r["_sin_mes"]).sum()))
print("  del anio 2010:", int((r["_anio"] == 2010).sum()),
      "| de otros anios:", int((r["_anio"] != 2010).sum()))
print("  con area positiva:", int((r["_area"] > 0).sum()), "(control: 576; con la estricta eran 572)",
      "| area cero:", int((r["_area"] == 0).sum()),
      "| area ausente:", int(r["_area"].isna().sum()))

vac = p[p["_dep_vacio"]]
print("\nFilas del principal con departamento vacio:", len(vac), "(control: 108)")
print("  de ellas, marcadas como repeticion:", int(vac["_rep"].sum()),
      "| primeras copias:", int((~vac["_rep"]).sum()))
print("\nRepeticiones por anio:")
print(r["_anio"].value_counts().sort_index().astype(int).to_string())
ver = int(r["_dep_vacio"].sum()) + int((~r["_dep_vacio"] & r["_sin_mes"]).sum()) + int((~r["_dep_vacio"] & ~r["_sin_mes"]).sum())
print("\nComprobacion: vacias + sin mes + con departamento y mes =", ver, "(debe ser igual al total de repeticiones)")
