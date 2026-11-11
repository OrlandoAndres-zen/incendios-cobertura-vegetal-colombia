"""
unificar_areas_protegidas.py  (G-07)

Crea dos columnas NUEVAS a partir de area_protegida (la original no se toca):
  - area_protegida_unificada: nombre unificado, solo cuando el texto es un nombre.
  - area_protegida_categoria:
        nombre | respuesta_no | respuesta_si | NA | por_revisar | vacio

Reglas (solo se unen formas que difieren por mayusculas, tildes, saltos de linea,
prefijo "PNN"/"Parque Nacional Natural", un articulo o una errata evidente):
  - Respuestas tipo "N", "NO", "Ninguna", "Ninguno" -> respuesta_no.
  - "S", "SI" -> respuesta_si (dicen que si, pero sin nombre).
  - "NA" y "N/A" -> NA (se leen con keep_default_na=False). Su significado NO esta
    confirmado: no se interpreta.
  - "PNN" y "DMI" solos estan incompletos -> por_revisar.
  - Nombres parecidos pero que pueden ser areas distintas (por ejemplo "El Cocuy" y
    "Sierra Nevada del Cocuy", "La Macarena" y "Sierra de la Macarena") NO se unen.
El diccionario UNIR es editable.

No cambia el CSV consolidado. Guarda en resultados/:
  areas_protegidas_unificada.csv       (archivo, hoja, fila_excel + columnas nuevas)
  areas_protegidas_equivalencias.csv   (cada forma original y a donde va)

Uso (dentro de entrega_incendios, con el .venv activo):
    python unificar_areas_protegidas.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
VERDADEROS = ["true", "1", "1.0", "si", "sí"]


def clave_suave(texto):
    """Mayusculas, sin tildes, sin signos y sin espacios repetidos."""
    t = unicodedata.normalize("NFKD", str(texto).upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return " ".join(t.split())


# Formas (clave suave) que se unen bajo un solo nombre. Editable.
UNIR = {
    "Parque Nacional Natural El Cocuy": ["PNN EL COCUY", "EL COCUY"],
    "Parque Nacional Natural El Tuparro": ["PARQUE NACIONAL NATURAL EL TUPARRO", "PNN EL TUPARRO", "EL TUPARRO"],
    "Parque Nacional Natural Farallones de Cali": ["PARQUE NACIONAL NATURAL FARALLONES DE CALI", "PNN FARALLONES DE CALI"],
    "Parque Nacional Natural Los Katíos": ["PNN KATIOS", "PARQUE NACIONAL NATURAL LOS KATIOS"],
    "Parque Nacional Natural Sierra de la Macarena": [
        "PARQUE NACIONAL NATURAL SIERRA DE LA MACARENA", "PNN SIERRA DE LA MACARENA",
        "PARQUE NACIONAL NATURAL SIERRA DE LA MACERENA"],
    "Parque Nacional Natural Sierra Nevada de Santa Marta": [
        "PARQUE NACIONAL NATURAL SIERRA NEVADA DE SANTA MARTA", "PNN SIERRA NEVADA DE SANTA MARTA"],
    "Parque Nacional Natural Los Nevados": ["PARQUE NACIONAL NATURAL LOS NEVADOS"],  # solo mayusculas
    "Parque Nacional Natural Las Hermosas": ["PARQUE NACIONAL NATURAL LAS HERMOSAS"],
    "Parque Nacional Natural Las Orquídeas": ["PARQUE NACIONAL NATURAL LAS ORQUIDEAS"],
    "Vía Parque Isla de Salamanca": ["VIA PARQUE ISLA DE SALAMANCA", "VIA PARQUE ISLA SALAMANCA"],
    "Santuario de Flora y Fauna Iguaque": ["SANTUARIO DE FAUNA Y FLORA IGUAQUE", "SANTUARIO DE FLORA Y FAUNA IGUAQUE"],
    "Santuario de Flora y Fauna Ciénaga Grande de Santa Marta": [
        "SANTUARIO DE FAUNA Y FLORA CIENAGA GRANDE DE SANTA MARTA",
        "SANTUARIO DE FLORA Y FAUNA CIENAGA GRANDE DE SANTA MARTA"],
    "Complejo de Páramo Tota-Bijagual-Mamapacha": [
        "COMPLEJO DE PARAMO TOTA BIJAGUAL MAMAPACHA", "COMPLEJO TOTA BIJAGUAL MAMAPACHA"],
    "Complejo Guantiva-La Rusia": ["COMPLEJO GUANTIVA LA RUSIA", "GUANTIVA LA RUSIA"],
    "Parque Natural Regional Unidad Biogeográfica Siscunsí-Oceta": [
        "PNR SISCUNCI OCETA", "PNR SISCUNSI OCETA", "PNR UNIDAD BIOGEOGRAFICA SISCUNSI OCETA",
        "PARQUE NATURAL REGIONAL UNIDAD BIOGEOGRAFICA SISCUNSI OCETA"],
}
CLAVE_A_NOMBRE = {c: nombre for nombre, claves in UNIR.items() for c in claves}

RESPUESTA_NO = {"N", "NO", "NINGUNA", "NINGUNO"}
RESPUESTA_SI = {"S", "SI"}
POR_REVISAR = {"PNN", "DMI"}
TEXTOS_NA = {"NA", "N A"}  # "NA" y "N/A" (la barra pasa a espacio en clave_suave)


def categoria_de(raw):
    v = str(raw).strip()
    if v == "":
        return "vacio"
    if v.upper() in ("NA", "N/A"):
        return "NA"
    c = clave_suave(v)
    if c in RESPUESTA_NO:
        return "respuesta_no"
    if c in RESPUESTA_SI:
        return "respuesta_si"
    if c in POR_REVISAR:
        return "por_revisar"
    return "nombre"


# 1. Carga (sin convertir "NA" en vacio) ----------------------------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False,
                 keep_default_na=False, dtype=str)
print("Filas del CSV:", len(df), "(control: 47.527)")
df["_principal"] = df["usar_principal"].str.strip().str.lower().isin(VERDADEROS)
print("Escenario principal:", int(df["_principal"].sum()), "(control: 45.166)")

df["_raw"] = df["area_protegida"].str.strip()
df["area_protegida_categoria"] = df["_raw"].map(categoria_de)

# 2. Nombre unificado -----------------------------------------------------------------
nombres = df[df["area_protegida_categoria"] == "nombre"].copy()
nombres["_clave"] = nombres["_raw"].map(clave_suave)
nombres["_limpio"] = nombres["_raw"].map(lambda t: " ".join(t.split()))

# Si en UNIR hay una clave que no aparece en los datos, avisar (puede ser una errata)
claves_datos = set(nombres["_clave"])
faltan = [c for c in CLAVE_A_NOMBRE if c not in claves_datos]
if faltan:
    print("\nATENCION: claves de UNIR que no aparecen en los datos:", faltan)

# Para los nombres que no se unen a mano: la forma escrita mas frecuente de cada clave
mas_frecuente = (nombres.groupby(["_clave", "_limpio"]).size().rename("n").reset_index()
                 .sort_values(["_clave", "n"], ascending=[True, False])
                 .drop_duplicates("_clave").set_index("_clave")["_limpio"])
nombres["area_protegida_unificada"] = nombres["_clave"].map(
    lambda c: CLAVE_A_NOMBRE.get(c, mas_frecuente[c]))
df["area_protegida_unificada"] = ""
df.loc[nombres.index, "area_protegida_unificada"] = nombres["area_protegida_unificada"]

# 3. Cifras de control (solo escenario principal) ------------------------------------
p = df[df["_principal"]]
print("\nCategorias en el escenario principal:")
print(p["area_protegida_categoria"].value_counts().to_string())
print("Suma de categorias:", len(p), "(control: 45.166)")
con_algo = int((~p["area_protegida_categoria"].isin(["vacio", "NA"])).sum())
print("Con area_protegida escrita (sin vacios ni NA):", con_algo, "(control: 881)")
print("Nombres de area protegida distintos antes:", p.loc[p["area_protegida_categoria"] == "nombre", "_raw"].nunique(),
      "| despues:", p.loc[p["area_protegida_categoria"] == "nombre", "area_protegida_unificada"].nunique())

print("\nNombres unificados con mas registros (principal):")
print(p[p["area_protegida_categoria"] == "nombre"]["area_protegida_unificada"].value_counts().head(12).to_string())

# 4. Que se unio con que ----------------------------------------------------------------
eq = (df.groupby(["_raw", "area_protegida_categoria", "area_protegida_unificada"])
      .size().rename("registros").reset_index().rename(columns={"_raw": "area_protegida_original"}))
eq["original_una_linea"] = eq["area_protegida_original"].map(lambda t: " ".join(t.split()))
eq = eq.sort_values(["area_protegida_categoria", "area_protegida_unificada", "registros"],
                    ascending=[True, True, False])
multi = eq[eq["area_protegida_categoria"] == "nombre"].groupby("area_protegida_unificada").filter(lambda g: len(g) > 1)
print("\nNombres que juntan varias formas escritas:")
for nombre, g in multi.groupby("area_protegida_unificada"):
    print("\n>>", nombre, "|", int(g["registros"].sum()), "registros (todas las filas)")
    print(g[["original_una_linea", "registros"]].to_string(index=False))

# 5. Guardar -------------------------------------------------------------------------------
clave_fila = ["archivo", "hoja", "fila_excel"]
print("\nFilas con la misma combinacion archivo-hoja-fila_excel repetida:", int(df.duplicated(clave_fila).sum()))
salida = df[clave_fila + ["area_protegida", "area_protegida_unificada", "area_protegida_categoria"]]
salida.to_csv(RES / "areas_protegidas_unificada.csv", index=False, encoding="utf-8-sig")
eq.drop(columns=["original_una_linea"]).to_csv(RES / "areas_protegidas_equivalencias.csv", index=False, encoding="utf-8-sig")
print("\nGuardado: areas_protegidas_unificada.csv y areas_protegidas_equivalencias.csv")
