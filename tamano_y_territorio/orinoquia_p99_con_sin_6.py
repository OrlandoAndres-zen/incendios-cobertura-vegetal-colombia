"""
Orinoquia: percentil 99 (y mediana, p90) de area_total con y sin los 6 registros
grandes marcados (M-12, M-14, M-16, M-17, M-18, M-24), por fase ENSO.

Solo escenario principal y area_total > 0 (hectareas). Fase ENSO pegada por anio y mes
desde resultados/serie_mensual_con_ONI.csv; registros de 2025 en adelante = "Sin fase"
(ANIO_MAX_ENSO = 2024). No modifica ningun archivo existente.
Salida: resultados/orinoquia_p99_con_sin_6.csv

Uso (dentro de entrega_incendios, con el .venv activo):
    python orinoquia_p99_con_sin_6.py
"""
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
ANIO_MAX_ENSO = 2024
ORINOQUIA = {"ARAUCA", "CASANARE", "META", "VICHADA"}
# (hoja, fila_excel, area esperada) de los 6 registros marcados
SEIS = {
    "M-12": ("BD_ICV_2010_2020", "16923", 11000.0),
    "M-14": ("BD_ICV_2010_2020", "16922", 10000.0),
    "M-16": ("BD_ICV_2021", "755", 41079.0),
    "M-17": ("BD_ICV_2022", "251", 35463.0),
    "M-18": ("BD_ICV_2022", "176", 26008.0),
    "M-24": ("BD_ICV_2022", "452", 12000.0),
}


def sin_tilde(t):
    t = unicodedata.normalize("NFKD", str(t))
    return "".join(c for c in t if not unicodedata.combining(c)).strip().upper()


d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", dtype=str, keep_default_na=False)
p = d[d["usar_principal"].str.strip().str.lower() == "true"].copy()
p["area"] = pd.to_numeric(p["area_total"], errors="coerce")
p["anio_n"] = pd.to_numeric(p["anio"], errors="coerce")
p["mes_n"] = pd.to_numeric(p["mes"], errors="coerce")
p["dep_n"] = p["departamento"].map(sin_tilde)
o = p[p["dep_n"].isin(ORINOQUIA) & (p["area"] > 0)].copy()
print("Orinoquia con area positiva:", len(o), "(control: 4902)")

# --- Los 6 registros ---
o["hoja_n"] = o["hoja"].str.strip()
o["id6"] = ""
print("\nLos 6 registros marcados:")
for k, (hoja, fila, esperada) in SEIS.items():
    m = (o["hoja_n"] == hoja) & (o["fila_excel"].str.strip() == fila)
    o.loc[m, "id6"] = k
    if m.sum() != 1:
        print(f"  {k}: ENCONTRADOS {int(m.sum())} (debia ser 1)  <-- REVISAR")
        continue
    a = float(o.loc[m, "area"].iloc[0])
    ok = "ok" if abs(a - esperada) < 1e-6 else f"NO COINCIDE (esperada {esperada})"
    print(f"  {k}: {o.loc[m,'municipio'].iloc[0]} {o.loc[m,'anio'].iloc[0]} fila {fila} area {a:,.0f} {ok}")
n6 = int((o["id6"] != "").sum())
print("Encontrados:", n6, "(control: 6)")

# --- Fase ENSO ---
fase = None
try:
    s = pd.read_csv(RES / "serie_mensual_con_ONI.csv", dtype=str, keep_default_na=False)
    if not {"anio", "mes", "fase_episodio"} <= set(s.columns):
        raise KeyError("faltan columnas anio / mes / fase_episodio")
    s["anio_n"] = pd.to_numeric(s["anio"], errors="coerce")
    s["mes_n"] = pd.to_numeric(s["mes"], errors="coerce")
    s["fase_n"] = s["fase_episodio"].map(sin_tilde)
    s = s.drop_duplicates(["anio_n", "mes_n"])[["anio_n", "mes_n", "fase_n"]]
    o = o.merge(s, on=["anio_n", "mes_n"], how="left")
    o["fase_n"] = o["fase_n"].fillna("SIN FASE")
    o.loc[o["anio_n"] > ANIO_MAX_ENSO, "fase_n"] = "SIN FASE"
    fase = True
except Exception as e:
    print("\nNO se pudo pegar la fase ENSO:", e)
    if "s" in dir():
        print("Columnas de serie_mensual_con_ONI.csv:", list(s.columns))
    o["fase_n"] = "SIN FASE"

if fase:
    print("\nRegistros por fase:", o["fase_n"].value_counts().to_dict())
    print("(control: EL NINO 2018, LA NINA 1042, NEUTRAL 1221, SIN FASE 621)")


def fila(sub, etiqueta):
    sin = sub[sub["id6"] == ""]["area"]
    con = sub["area"]
    r = {"grupo": etiqueta, "n_con": len(con), "n_sin6": len(sin),
         "mediana_con": con.median(), "mediana_sin6": sin.median(),
         "p90_con": con.quantile(0.90), "p90_sin6": sin.quantile(0.90),
         "p99_con": con.quantile(0.99), "p99_sin6": sin.quantile(0.99),
         "max_con": con.max(), "max_sin6": sin.max()}
    r["p99_cambio_pct"] = 100 * (r["p99_sin6"] / r["p99_con"] - 1)
    return r


filas = [fila(o, "Orinoquia todos")]
if fase:
    for f in ["EL NINO", "LA NINA", "NEUTRAL", "SIN FASE"]:
        sub = o[o["fase_n"] == f]
        if len(sub):
            filas.append(fila(sub, f))
t = pd.DataFrame(filas)
t.to_csv(RES / "orinoquia_p99_con_sin_6.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
print("\nCon y sin los 6 registros (hectareas):")
print(t.round(1).to_string(index=False))
print("\nCeldas con n < 30 no son confiables.")
print("Guardado: resultados/orinoquia_p99_con_sin_6.csv")
