"""
revisar_108_vacios.py

Revisa los registros del escenario principal que no tienen departamento ni municipio.
Para cada uno cuenta cuantas columnas de contenido tienen algun dato
(vereda, predio, coordenadas, tipos de incendio, causas, coberturas, area).
Una celda se cuenta como "sin dato" si esta vacia o vale 0.

Uso (dentro de entrega_incendios, con el .venv activo):
    python revisar_108_vacios.py
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = BASE / "resultados" / "revision_108_sin_departamento.csv"

CONTENIDO = [
    "vereda", "predio", "area_protegida", "latitud_original", "longitud_original",
    "elevacion", "tipo_copa", "tipo_superficial", "tipo_subterraneo", "tipo_mixto",
    "tipo_otro", "causa_quema", "causa_negligencia", "causa_intencional",
    "causa_accidental", "causa_reactivacion", "causa_otra", "bosque_denso",
    "bosque_intervenido", "bosque_plantado", "bosque_seco", "cultivos", "paramo",
    "sabana_pastizal", "pastos_manejados", "rastrojo", "vegetacion_seca",
    "cobertura_indeterminada", "area_total_original",
]


def con_dato(valor):
    if pd.isna(valor):
        return False
    texto = str(valor).strip()
    if texto == "" or texto.lower() == "nan":
        return False
    try:
        return float(texto.replace(",", ".")) != 0
    except ValueError:
        return True


df = pd.read_csv(CSV, low_memory=False)
principal = df["usar_principal"].astype(str).str.lower().isin(["true", "1"])
df = df[principal].copy()
print("Escenario principal:", len(df), "(control: 45.166)")

sin_dep = df["departamento"].map(lambda v: not con_dato(v))
sin_mun = df["municipio"].map(lambda v: not con_dato(v))
vacios = df[sin_dep & sin_mun].copy()
print("Sin departamento ni municipio:", len(vacios), "(esperado: 108)")

cols = [c for c in CONTENIDO if c in vacios.columns]
faltan = [c for c in CONTENIDO if c not in vacios.columns]
if faltan:
    print("Columnas que no encontre (se ignoran):", faltan)


def listar(fila):
    return ", ".join(c for c in cols if con_dato(fila[c]))


vacios["columnas_con_dato"] = vacios.apply(listar, axis=1)
vacios["n_columnas_con_dato"] = vacios["columnas_con_dato"].map(
    lambda t: 0 if t == "" else len(t.split(", "))
)

totalmente = (vacios["n_columnas_con_dato"] == 0).sum()
print("\nTotalmente vacios (ninguna columna de contenido con dato):", totalmente)
print("Con algun dato:", len(vacios) - totalmente)

print("\nPor anio:")
print(vacios["anio"].value_counts().sort_index().to_string())
print("\nPor archivo:")
print(vacios["archivo"].value_counts().to_string())

con_algo = vacios[vacios["n_columnas_con_dato"] > 0]
if len(con_algo):
    print("\nLos que SI tienen algun dato (hasta 15):")
    print(
        con_algo[["archivo", "fila_excel", "anio", "n_columnas_con_dato", "columnas_con_dato"]]
        .head(15)
        .to_string(index=False)
    )

salida = vacios[
    ["archivo", "hoja", "fila_excel", "anio", "mes_original", "n_columnas_con_dato", "columnas_con_dato"]
].sort_values(["archivo", "fila_excel"])
salida.to_csv(SALIDA, index=False, encoding="utf-8")
print("\nGuardado en:", SALIDA)
