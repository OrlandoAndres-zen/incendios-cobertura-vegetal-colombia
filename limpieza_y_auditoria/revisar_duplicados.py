"""
Aclara por qué el resumen de auditoría habla de 773 repeticiones exactas
posteriores y la columna duplicado_exacto_posterior marca más filas.

Ejecutar desde entrega_incendios/ con el entorno activo:
    python revisar_duplicados.py

Solo lee archivos y calcula; no modifica nada.
"""
import json
from pathlib import Path

import pandas as pd

RES = Path(__file__).resolve().parent / "resultados"
VERDADEROS = ["true", "1", "1.0", "si", "sí"]


def bandera(serie):
    return serie.astype(str).str.strip().str.lower().isin(VERDADEROS)


def buscar(obj, ruta=""):
    """Devuelve (ruta, valor) de toda clave que contenga 'dupl'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            r = f"{ruta}/{k}" if ruta else str(k)
            if "dupl" in str(k).lower() and not isinstance(v, (dict, list)):
                yield r, v
            yield from buscar(v, r)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from buscar(v, f"{ruta}[{i}]")


# 1. Lo que dice el resumen de auditoría ------------------------------------------
print("Cifras de duplicados en resumen_auditoria.json:")
with open(RES / "resumen_auditoria.json", encoding="utf-8") as f:
    for ruta, valor in buscar(json.load(f)):
        print(f"  {ruta}: {valor}")

# 2. Lo que dicen las columnas del CSV ----------------------------------------------
d = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
principal = bandera(d["usar_principal"])
post = bandera(d["duplicado_exacto_posterior"])
cand = bandera(d["duplicado_exacto_candidato"])
area = pd.to_numeric(d["area_total"], errors="coerce")

print(f"\nFilas totales: {len(d)}")
print(f"Escenario principal: {int(principal.sum())}")
print(f"\nColumna duplicado_exacto_posterior:")
print(f"  en todo el CSV: {int(post.sum())}")
print(f"  dentro del principal: {int((post & principal).sum())}")
print(f"  dentro del principal con área positiva: {int((post & principal & (area > 0)).sum())}")
print(f"  fuera del principal: {int((post & ~principal).sum())}")
print(f"Columna duplicado_exacto_candidato dentro del principal: {int((cand & principal).sum())}")

# 3. Repeticiones recalculadas solo dentro del escenario principal -----------------------
excluir = {"archivo", "hoja", "fila_excel", "usar_principal",
           "duplicado_exacto_candidato", "duplicado_exacto_posterior"}
columnas = [c for c in d.columns if c not in excluir]
sub = d[principal]
rep = pd.Series(False, index=d.index)
rep.loc[sub.index] = sub.duplicated(subset=columnas, keep="first")

print(f"\nRepeticiones exactas recalculadas dentro del principal "
      f"(todas las columnas de contenido): {int(rep.sum())}")
marcadas = post & principal
print(f"De las {int(marcadas.sum())} marcadas como posteriores en el principal:")
print(f"  siguen siendo repetición dentro del principal: {int((marcadas & rep).sum())}")
print(f"  su copia anterior está fuera del principal: {int((marcadas & ~rep).sum())}")

print("\nMarcadas posteriores en el principal, por año (las 8 con más):")
print(d.loc[marcadas, "anio"].value_counts().head(8).to_string())
print("\nPor archivo:")
print(d.loc[marcadas, "archivo"].value_counts().to_string())
