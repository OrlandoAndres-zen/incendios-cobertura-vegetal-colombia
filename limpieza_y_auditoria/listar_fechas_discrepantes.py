"""
listar_fechas_discrepantes.py  (G-02)

Lista los registros cuyo mes declarado (columna mes) no coincide con el mes de su
fecha, y los que tienen el anio distinto. Guarda una tabla con archivo, hoja y
fila_excel para poder mirar algunas filas en el Excel original.
Solo calcula: no cambia ningun dato.

Control (segun la auditoria): 96 con mes distinto y 1 con anio distinto.
"mes - mes_fecha" positivo = la fecha cae ANTES del mes declarado.

Uso (dentro de entrega_incendios, con el .venv activo):
    python listar_fechas_discrepantes.py
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
NECESARIAS = ["archivo", "hoja", "fila_excel", "anio", "mes_original", "mes", "fecha",
              "departamento", "municipio", "area_total", "usar_principal"]

d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
faltan = [c for c in NECESARIAS if c not in d.columns]
if faltan:
    raise SystemExit("Faltan columnas: " + str(faltan) + "\nColumnas disponibles: " + str(list(d.columns)))
print("Filas del CSV:", len(d), "(control: 47.527)")

# La columna mezcla "2015-08-04" y "2015-08-04 00:00:00": se leen las dos formas.
d["_fecha"] = pd.to_datetime(d["fecha"], format="ISO8601", errors="coerce")
print("Ejemplos de la columna fecha:", d["fecha"].dropna().astype(str).head(3).tolist())
print("Filas sin fecha (celda vacia):", int(d["fecha"].isna().sum()))
print("Filas con fecha escrita que NO se pudo leer:", int((d["fecha"].notna() & d["_fecha"].isna()).sum()), "(debe ser 0)")

d["_mes"] = pd.to_numeric(d["mes"], errors="coerce")
d["_anio"] = pd.to_numeric(d["anio"], errors="coerce")
d["mes_fecha"] = d["_fecha"].dt.month
d["anio_fecha"] = d["_fecha"].dt.year
tiene = d["_fecha"].notna() & d["_mes"].notna() & d["_anio"].notna()

mes_dist = tiene & (d["_mes"] != d["mes_fecha"])
anio_dist = tiene & (d["_anio"] != d["anio_fecha"])
d["meses_de_diferencia"] = (d["_anio"] * 12 + d["_mes"]) - (d["anio_fecha"] * 12 + d["mes_fecha"])

print("\nMes declarado distinto del mes de la fecha:", int(mes_dist.sum()), "(control: 96)")
print("Anio distinto:", int(anio_dist.sum()), "(control: 1)")

sel = d[mes_dist | anio_dist].copy()
sel["tipo"] = ["anio" if a else "mes" for a in anio_dist[sel.index]]
print("Total en la lista:", len(sel), "(control: 97)")

m = sel[sel["tipo"] == "mes"]
print("\nPor diferencia (solo los de mes). Positivo = la fecha cae antes del mes declarado:")
print(m["meses_de_diferencia"].value_counts().sort_index().astype(int).to_string())
print("Fecha ANTES del mes declarado:", int((m["meses_de_diferencia"] > 0).sum()), "(control: 86)")
print("Exactamente un mes antes:", int((m["meses_de_diferencia"] == 1).sum()), "(control: 68)")
print("\nPor archivo:")
print(sel["archivo"].value_counts().to_string())
print("\nPor anio:")
print(sel["_anio"].value_counts().sort_index().astype(int).to_string())

cols = ["archivo", "hoja", "fila_excel", "anio", "mes_original", "mes", "fecha", "mes_fecha",
        "anio_fecha", "meses_de_diferencia", "tipo", "departamento", "municipio", "area_total", "usar_principal"]
sel = sel.sort_values(["_anio", "archivo", "fila_excel"])[cols]
sel.to_csv(RES / "fechas_discrepantes.csv", index=False, encoding="utf-8-sig")

print("\nPrimeros 6 registros de 2003 (para mirar en el Excel):")
print(sel[sel["anio"] == 2003].head(6)[["archivo", "hoja", "fila_excel", "mes_original", "fecha"]].to_string(index=False))
print("\nGuardado: resultados/fechas_discrepantes.csv")
