"""
revisar_areas_protegidas.py  (G-07)

Cuenta cuantas formas distintas hay de escribir la columna area_protegida
en el escenario principal y las agrupa para que Orlando y Julian decidan
como unificarlas. NO cambia ningun dato: solo calcula y guarda una tabla.

Uso (dentro de entrega_incendios, con el .venv activo):
    python revisar_areas_protegidas.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = BASE / "resultados" / "areas_protegidas_variantes.csv"

# Palabras de prefijo que se quitan SOLO para agrupar y revisar (no para unir solas)
PREFIJOS = {"PARQUE", "NACIONAL", "NATURAL", "PNN", "PN", "P", "N"}


def sin_tildes(texto):
    t = unicodedata.normalize("NFKD", str(texto).upper())
    return "".join(c for c in t if not unicodedata.combining(c))


def clave_suave(texto):
    """Mayusculas, sin tildes, sin signos y sin espacios repetidos."""
    t = re.sub(r"[^A-Z0-9]+", " ", sin_tildes(texto))
    return " ".join(t.split())


def clave_corta(texto):
    """Como la suave, pero sin las palabras de prefijo (Parque Nacional Natural, PNN)."""
    palabras = [p for p in clave_suave(texto).split() if p not in PREFIJOS]
    return " ".join(palabras)


def con_dato(valor):
    if pd.isna(valor):
        return False
    t = str(valor).strip()
    return t != "" and t.lower() != "nan" and t != "0"


df = pd.read_csv(CSV, low_memory=False)
print("Filas del CSV:", len(df), "(control: 47.527)")

principal = df["usar_principal"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "si", "sí"])
df = df[principal].copy()
print("Escenario principal:", len(df), "(control: 45.166)")

tiene = df["area_protegida"].map(con_dato)
print("Con area_protegida escrita:", int(tiene.sum()), "(sin cifra de control: anotala)")

d = df[tiene].copy()
d["area_protegida"] = d["area_protegida"].astype(str).str.strip()

tabla = d.groupby("area_protegida").size().rename("registros").reset_index()
tabla["clave_suave"] = tabla["area_protegida"].map(clave_suave)
tabla["clave_corta"] = tabla["area_protegida"].map(clave_corta)

print("\nFormas distintas de escribirla (texto exacto):", len(tabla))
print("Distintas despues de normalizar (clave suave):", tabla["clave_suave"].nunique())
print("Distintas despues de quitar prefijos (clave corta):", tabla["clave_corta"].nunique())

# Grupos de la clave corta que tienen mas de una forma escrita
por_grupo = tabla.groupby("clave_corta")
grupos = por_grupo.agg(
    formas=("area_protegida", "size"),
    registros=("registros", "sum"),
).reset_index()
varios = grupos[grupos["formas"] > 1].sort_values("registros", ascending=False)
print("\nGrupos con mas de una forma escrita:", len(varios))

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)
for _, g in varios.head(10).iterrows():
    sub = tabla[tabla["clave_corta"] == g["clave_corta"]].sort_values("registros", ascending=False)
    print("\n>>", g["clave_corta"] or "(vacio)", "|", int(g["registros"]), "registros")
    print(sub[["area_protegida", "registros"]].to_string(index=False))

# Las 15 mas frecuentes, para ver el tamano del problema
print("\nLas 15 formas mas frecuentes:")
print(tabla.sort_values("registros", ascending=False).head(15)[["area_protegida", "registros"]].to_string(index=False))

tabla = tabla.sort_values(["clave_corta", "registros"], ascending=[True, False])
tabla.to_csv(SALIDA, index=False, encoding="utf-8-sig")
print("\nGuardado en:", SALIDA)
