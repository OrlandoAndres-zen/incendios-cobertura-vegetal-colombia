# G-05: convierte grados, minutos y segundos (DMS) a decimal, solo para 3 filas de Cumaribo 2017.
# No modifica ningun archivo existente. Escribe resultados/g05_coordenadas_convertidas.csv
import re
import pandas as pd
from pathlib import Path

RUTA = Path(__file__).parent / "resultados" / "incendios_consolidados_auditados.csv"
SALIDA = Path(__file__).parent / "resultados" / "g05_coordenadas_convertidas.csv"
FILAS = ["15113", "15115", "15133"]
# Valores calculados a mano (para comparar)
MANUAL = {"15113": (5.2406, -68.3358), "15115": (5.1883, -69.0575), "15133": (5.3789, -68.1131)}

PAT = re.compile(r"^\s*(\d+)\s*°\s*(\d+)\s*['’′]\s*([\d.,]+)\s*(?:''|\"|”|″|’’)?\s*([NSEWnsew])?\s*$")

def dms_a_decimal(txt, es_longitud):
    m = PAT.match(txt)
    if not m:
        return None
    g, mi, s, hemi = m.groups()
    valor = int(g) + int(mi) / 60 + float(s.replace(",", ".")) / 3600
    hemi = (hemi or "").upper()
    # Colombia: longitud oeste y latitud norte. Si no trae letra, se supone el signo esperado.
    if es_longitud:
        negativo = hemi != "E"
    else:
        negativo = hemi == "S"
    return -valor if negativo else valor

d = pd.read_csv(RUTA, dtype=str, keep_default_na=False)
sel = d[d["archivo"].str.contains("2010_2020") & d["fila_excel"].isin(FILAS)].copy()
print("Filas encontradas:", len(sel))

sel["lat_dms_decimal"] = sel["latitud_original"].apply(lambda t: dms_a_decimal(t, False))
sel["lon_dms_decimal"] = sel["longitud_original"].apply(lambda t: dms_a_decimal(t, True))
sel["lat_manual"] = sel["fila_excel"].map(lambda f: MANUAL[f][0])
sel["lon_manual"] = sel["fila_excel"].map(lambda f: MANUAL[f][1])
sel["dif_lat"] = (sel["lat_dms_decimal"] - sel["lat_manual"]).abs()
sel["dif_lon"] = (sel["lon_dms_decimal"] - sel["lon_manual"]).abs()

cols = ["archivo", "hoja", "fila_excel", "latitud_original", "longitud_original",
        "lat_dms_decimal", "lon_dms_decimal", "lat_manual", "lon_manual", "dif_lat", "dif_lon"]
sel = sel[cols]
sel.to_csv(SALIDA, index=False, encoding="utf-8")

pd.set_option("display.width", 200)
print(sel[["fila_excel", "lat_dms_decimal", "lon_dms_decimal", "dif_lat", "dif_lon"]].round(5).to_string(index=False))
ok = sel[["dif_lat", "dif_lon"]].max().max() < 0.0001
print("Todas las diferencias con lo manual < 0,0001:", "SI" if ok else "NO")
print("Guardado en:", SALIDA)
