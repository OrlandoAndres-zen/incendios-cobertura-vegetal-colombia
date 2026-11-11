# Compara dos definiciones de repeticion dentro del escenario principal:
#  - ESTRICTA: textos tal cual (la que dio 767)
#  - UNIFICADA: sin mayusculas, sin espacios al inicio/final ni dobles (la de Julian, 773)
# No modifica ningun archivo existente. Escribe resultados/repeticiones_estricta_vs_unificada.csv
import re
import pandas as pd
from pathlib import Path

RUTA = Path(__file__).parent / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = Path(__file__).parent / "resultados" / "repeticiones_estricta_vs_unificada.csv"

d = pd.read_csv(RUTA, dtype=str, keep_default_na=False)
print("Filas del CSV:", len(d))

p = d[d["usar_principal"].str.strip().str.lower() == "true"].copy()
print("Escenario principal:", len(p))

# Columnas que NO se comparan: procedencia y banderas
EXCLUIR_EXACTAS = {"archivo", "hoja", "fila_excel", "usar_principal"}
EXCLUIR_PARTES = ("duplicado", "conflicto", "bandera", "revision", "sospech")
cols = [c for c in p.columns
        if c not in EXCLUIR_EXACTAS and not any(t in c.lower() for t in EXCLUIR_PARTES)]
print("Columnas comparadas:", len(cols))
print(cols)

def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()

llave_estricta = p[cols].agg("\x1f".join, axis=1)
llave_unificada = p[cols].map(norm).agg("\x1f".join, axis=1)

p["rep_estricta"] = llave_estricta.duplicated(keep="first")
p["rep_unificada"] = llave_unificada.duplicated(keep="first")
p["area_pos"] = pd.to_numeric(p["area_total"], errors="coerce") > 0

print()
print("Repeticiones ESTRICTAS :", int(p["rep_estricta"].sum()),
      "| con area positiva:", int((p["rep_estricta"] & p["area_pos"]).sum()))
print("Repeticiones UNIFICADAS:", int(p["rep_unificada"].sum()),
      "| con area positiva:", int((p["rep_unificada"] & p["area_pos"]).sum()))

solo = p[p["rep_unificada"] & ~p["rep_estricta"]].copy()
print("Solo en la definicion unificada:", len(solo))
print("Estricta que no esta en la unificada (debe ser 0):", int((p["rep_estricta"] & ~p["rep_unificada"]).sum()))

# Primera copia de cada una
primera = p.assign(_k=llave_unificada).drop_duplicates("_k", keep="first").set_index("_k")
solo["_k"] = llave_unificada[solo.index]
for c in ["archivo", "hoja", "fila_excel", "vereda"]:
    solo["primera_" + c] = solo["_k"].map(primera[c])

cols_sal = ["archivo", "hoja", "fila_excel", "vereda",
            "primera_archivo", "primera_hoja", "primera_fila_excel", "primera_vereda"]
solo = solo[cols_sal]
solo.to_csv(SALIDA, index=False, encoding="utf-8")

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 40)
if len(solo):
    mostrar = solo.copy()
    mostrar["hoja"] = mostrar["hoja"].map(repr)
    print()
    print(mostrar[["archivo", "hoja", "fila_excel", "vereda", "primera_fila_excel", "primera_vereda"]].to_string(index=False))
print("Guardado en:", SALIDA)
