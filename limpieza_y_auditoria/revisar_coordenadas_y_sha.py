"""
Solo LEE. No modifica ningun archivo.

Que hace:
1. Cuenta registros, escenario principal, coordenadas informadas y plausibles.
2. Busca las 3 filas del G-05 (Cumaribo 2017) y suma las que se agregan al convertir.
3. Busca si existe SHA256SUMS.txt y cuenta originales y scripts.

Como usarlo: copiarlo dentro de la carpeta entrega_incendios y correr:
    python revisar_coordenadas_y_sha.py
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
CSV = AQUI / "resultados" / "incendios_consolidados_auditados.csv"

# Valores convertidos a mano y con convertir_dms_g05.py (del resumen v7)
G05 = {
    15113: (5.24056, -68.33583),
    15115: (5.18833, -69.05750),
    15133: (5.37889, -68.11306),
}
# Rango amplio de Colombia (solo para descartar valores imposibles)
LAT_MIN, LAT_MAX = -4.3, 13.5
LON_MIN, LON_MAX = -79.1, -66.8


def es_verdadero(serie):
    return serie.astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])


def main():
    if not CSV.exists():
        print(f"No encuentro {CSV}. Pon el script dentro de entrega_incendios.")
        return

    df = pd.read_csv(CSV, low_memory=False)
    principal = es_verdadero(df["usar_principal"])
    informadas = es_verdadero(df["coordenadas_informadas"])
    plausibles = es_verdadero(df["coordenadas_decimales_plausibles"])

    print("=== 1. CONTEO GENERAL ===")
    print(f"Filas totales:                 {len(df):,}".replace(",", "."))
    print(f"Escenario principal:           {principal.sum():,}".replace(",", "."))
    print(f"Con coordenadas informadas:    {(principal & informadas).sum():,}".replace(",", "."))
    print(f"Plausibles (antes de G-05):    {(principal & plausibles).sum():,}".replace(",", "."))

    print("\n=== 2. LAS 3 FILAS DEL G-05 ===")
    en_archivo = df["archivo"].astype(str).str.contains("2010_2020")
    agregadas = 0
    encontradas = 0
    for fila, (lat, lon) in G05.items():
        m = (df["fila_excel"] == fila) & en_archivo
        if m.sum() != 1:
            print(f"Fila {fila}: NO encontrada de forma unica ({m.sum()} coincidencias)")
            continue
        encontradas += 1
        i = df.index[m][0]
        en_principal = bool(principal[i])
        ya_plausible = bool(plausibles[i])
        en_rango = (LAT_MIN <= lat <= LAT_MAX) and (LON_MIN <= lon <= LON_MAX)
        suma = en_principal and (not ya_plausible) and en_rango
        agregadas += int(suma)
        print(
            f"Fila {fila}: principal={en_principal}, "
            f"plausible_antes={ya_plausible}, en_rango_Colombia={en_rango}, "
            f"se_suma={suma}"
        )
    print(f"Encontradas: {encontradas} de 3")

    total = (principal & plausibles).sum() + agregadas
    print("\n=== CIFRA PARA EL ARTICULO ===")
    print(f"Plausibles despues de convertir G-05: {total:,}".replace(",", "."))
    print(f"(plausibles antes {(principal & plausibles).sum()} + agregadas {agregadas})")

    print("\n=== 3. REPRODUCIBILIDAD ===")
    sha = list(AQUI.rglob("SHA256SUMS*"))
    if sha:
        for p in sha:
            print(f"SHA256SUMS encontrado: {p.relative_to(AQUI)}")
    else:
        print("SHA256SUMS.txt NO existe en esta carpeta.")
    originales = AQUI / "originales"
    if originales.exists():
        archivos = sorted(p.name for p in originales.iterdir() if p.is_file())
        print(f"Originales ({len(archivos)}): {archivos}")
    else:
        print("No existe la carpeta originales/.")
    scripts = sorted(p.name for p in AQUI.glob("*.py"))
    print(f"Scripts .py en la carpeta ({len(scripts)}): {scripts}")


if __name__ == "__main__":
    main()
