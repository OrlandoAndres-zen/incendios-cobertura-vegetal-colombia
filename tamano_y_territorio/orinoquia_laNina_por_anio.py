"""
orinoquia_laNina_por_anio.py

Comprueba si, en la Orinoquia, los incendios de La Nina salen mas grandes y
si eso depende de pocos anios, de pocos registros o de los anios recientes.
Solo area_total > 0 del escenario principal. Region Orinoquia = Arauca, Casanare,
Meta y Vichada (misma definicion de tamanos_region_ENSO.py).

Calcula:
  1. Tamano por fase ENSO en cuatro casos:
       todos los meses | solo dic-mar, cada uno con todos los anios y sin 2024-2025.
  2. Tamano por anio y fase (todos los meses).
  3. Tamano por departamento y fase (solo dic-mar).
  4. Los 10 registros mas grandes de La Nina en la Orinoquia.
Es descriptivo: no prueba causalidad. area_total esta en hectareas.
Celdas con menos de 30 registros llevan * (no son confiables).

Uso (dentro de entrega_incendios, con el .venv activo):
    python orinoquia_laNina_por_anio.py
"""
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
MIN_N = 30
MESES_SECOS = [12, 1, 2, 3]
ANIO_MAX_ENSO = 2024  # ultimo anio que entra en las comparaciones ENSO
ORINOQUIA = ["ARAUCA", "CASANARE", "META", "VICHADA"]


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


def marca(v, n):
    if pd.isna(v):
        return "-"
    return f"{v:,.1f}" + ("*" if n < MIN_N else "")


def resumen(d, por):
    g = d.groupby(por)["area_total"]
    return g.agg(n="size", mediana="median", p75=lambda s: s.quantile(0.75),
                 p90=lambda s: s.quantile(0.90), maximo="max").reset_index()


def mostrar(t, filas, titulo):
    """Tabla con una columna por fase para n, mediana, p90 y maximo."""
    print("\n" + titulo)
    out = pd.DataFrame(index=sorted(t[filas].unique()))
    for fase in sorted(t["fase_episodio"].unique()):
        sub = t[t["fase_episodio"] == fase].set_index(filas)
        out[fase + " n"] = sub["n"].reindex(out.index).fillna(0).astype(int)
        out[fase + " mediana"] = [marca(sub["mediana"].get(i), sub["n"].get(i, 0)) for i in out.index]
        out[fase + " p90"] = [marca(sub["p90"].get(i), sub["n"].get(i, 0)) for i in out.index]
    print(out.to_string())


# 1. Datos --------------------------------------------------------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
df = df[df["usar_principal"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "si", "sí"])].copy()
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df = df[df["area_total"] > 0].copy()
print("Registros con area positiva:", len(df), "(control: 41.746)")

df["dep"] = df["departamento"].map(normalizar)
df = df[df["dep"].isin(ORINOQUIA)].copy()
print("Registros con area positiva en la Orinoquia:", len(df))

oni = pd.read_csv(RES / "serie_mensual_con_ONI.csv")[["anio", "mes", "fase_episodio"]].drop_duplicates(["anio", "mes"])
for c in ("anio", "mes"):
    oni[c] = pd.to_numeric(oni[c], errors="coerce").astype("Int64")
    df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
df = df.merge(oni, on=["anio", "mes"], how="left")
df["fase_episodio"] = df["fase_episodio"].fillna("Sin fase")
# Regla del proyecto (FUENTES.md): el analisis ENSO usa 2002-2024; 2025 no entra
# en las comparaciones principales.
pasan = (df["anio"] > ANIO_MAX_ENSO) & (df["fase_episodio"] != "Sin fase")
print(f"Registros de {ANIO_MAX_ENSO + 1} en adelante pasados a 'Sin fase': {int(pasan.sum())}")
df.loc[df["anio"] > ANIO_MAX_ENSO, "fase_episodio"] = "Sin fase"
print("Por fase:", df["fase_episodio"].value_counts().to_dict())
df = df[df["fase_episodio"] != "Sin fase"].copy()
print("Registros de la Orinoquia con fase:", len(df))

# 2. Cuatro casos: meses x anios -------------------------------------------------------
casos = {
    "todos los meses, todos los anios": df,
    "todos los meses, sin 2024-2025": df[~df["anio"].isin([2024, 2025])],
    "dic-mar, todos los anios": df[df["mes"].isin(MESES_SECOS)],
    "dic-mar, sin 2024-2025": df[df["mes"].isin(MESES_SECOS) & ~df["anio"].isin([2024, 2025])],
}
filas = []
for nombre, d in casos.items():
    t = resumen(d, "fase_episodio")
    t.insert(0, "caso", nombre)
    filas.append(t)
    print("\n=== " + nombre + " ===")
    print(t.drop(columns="caso").assign(
        mediana=lambda x: x["mediana"].round(1), p75=lambda x: x["p75"].round(1),
        p90=lambda x: x["p90"].round(1)).to_string(index=False))
pd.concat(filas).to_csv(RES / "orinoquia_fase_casos.csv", index=False, encoding="utf-8-sig")

# 3. Por anio y fase --------------------------------------------------------------------
por_anio = resumen(df, ["anio", "fase_episodio"])
por_anio.to_csv(RES / "orinoquia_por_anio_fase.csv", index=False, encoding="utf-8-sig")
mostrar(por_anio, "anio", "POR ANIO Y FASE (todos los meses; * = menos de 30 registros):")

# 4. Por departamento, solo dic-mar ------------------------------------------------------
por_dep = resumen(casos["dic-mar, todos los anios"], ["dep", "fase_episodio"])
por_dep.to_csv(RES / "orinoquia_por_departamento_dic_mar.csv", index=False, encoding="utf-8-sig")
mostrar(por_dep, "dep", "POR DEPARTAMENTO Y FASE (solo dic-mar):")

# 5. Los mayores de La Nina ----------------------------------------------------------------
ln = df[df["fase_episodio"].map(normalizar) == "LA NINA"].sort_values("area_total", ascending=False)  # sin depender de la tilde
print("\nLos 10 registros mas grandes de La Nina en la Orinoquia (hectareas):")
print(ln[["anio", "mes", "departamento", "municipio", "area_total"]].head(10).to_string(index=False))
n_ln = len(ln)
if n_ln == 0:
    print("ATENCION: no se encontraron registros de La Nina. Mandame la salida.")
print("\nRegistros de La Nina en la Orinoquia:", n_ln, "| anios distintos:", ln["anio"].nunique())
print("Los 5 anios con mas registros de La Nina:")
print(ln["anio"].value_counts().head(5).to_string())

print("\nGuardado: orinoquia_fase_casos.csv, orinoquia_por_anio_fase.csv, orinoquia_por_departamento_dic_mar.csv")
