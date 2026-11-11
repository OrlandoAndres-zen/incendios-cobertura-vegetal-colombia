"""
Dos mapas por departamento (paso 4):
  1. Número de registros de incendios
  2. Suma del área reportada (area_total > 0)

Antes de correrlo:
  - Descargar los límites departamentales del DANE (Marco Geoestadístico
    Nacional, nivel departamento, formato shapefile) y descomprimirlos en
    la carpeta  entrega_incendios/limites_dane/
  - Instalar la librería que lee shapefiles:  pip install pyshp

Ejecutar desde entrega_incendios/ con el entorno activo:
    python mapas_departamentos.py

Los departamentos se unen con los límites por código DANE (DIVIPOLA, 2 dígitos).
area_total está en hectáreas (IDEAM, radicado 20265000183351, 26 oct 2026).
"""
import textwrap
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

try:
    import shapefile  # librería pyshp
except ImportError:
    raise SystemExit("Falta la librería pyshp. Instálala con:  pip install pyshp")

BASE = Path(__file__).resolve().parent
RES = BASE / "resultados"
CARPETA_LIMITES = BASE / "limites_dane"

# Códigos DANE (DIVIPOLA) de departamento
CODIGOS = {
    "ANTIOQUIA": "05", "ATLANTICO": "08", "BOLIVAR": "13", "BOYACA": "15",
    "CALDAS": "17", "CAQUETA": "18", "CAUCA": "19", "CESAR": "20",
    "CORDOBA": "23", "CUNDINAMARCA": "25", "CHOCO": "27", "HUILA": "41",
    "LA GUAJIRA": "44", "MAGDALENA": "47", "META": "50", "NARINO": "52",
    "NORTE DE SANTANDER": "54", "QUINDIO": "63", "RISARALDA": "66",
    "SANTANDER": "68", "SUCRE": "70", "TOLIMA": "73", "VALLE DEL CAUCA": "76",
    "ARAUCA": "81", "CASANARE": "85", "PUTUMAYO": "86", "AMAZONAS": "91",
    "GUAINIA": "94", "GUAVIARE": "95", "VAUPES": "97", "VICHADA": "99",
}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


def codigo_de(nombre):
    n = normalizar(nombre)
    if n.startswith("BOGOTA"):
        return "11"
    if "SAN ANDRES" in n:
        return "88"
    return CODIGOS.get(n)


# 1. Datos: escenario principal por departamento -----------------------------
df = pd.read_csv(RES / "incendios_consolidados_auditados.csv", low_memory=False)
df = df[
    df["usar_principal"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "1.0", "si", "sí"])
].copy()
df["area_total"] = pd.to_numeric(df["area_total"], errors="coerce")
df["codigo_dane"] = df["departamento"].map(codigo_de)
anios = pd.to_numeric(df["anio"], errors="coerce")
periodo = f"{int(anios.min())}-{int(anios.max())}"

print(f"Registros en el escenario principal: {len(df)}")  # esperado 45166
sin_codigo = df.loc[df["codigo_dane"].isna(), "departamento"].value_counts()
if len(sin_codigo):
    print("\nAVISO: departamentos sin código DANE (no saldrán en el mapa):")
    print(sin_codigo.to_string())

pos = df[df["area_total"] > 0]
tabla = pd.DataFrame({
    "departamento": df.groupby("codigo_dane")["departamento"].agg(lambda s: s.mode().iat[0]),
    "n_registros": df.groupby("codigo_dane").size(),
    "n_area_positiva": pos.groupby("codigo_dane").size(),
    "suma_area": pos.groupby("codigo_dane")["area_total"].sum(),
    "mediana_area": pos.groupby("codigo_dane")["area_total"].median(),
})
tabla[["n_area_positiva", "suma_area"]] = tabla[["n_area_positiva", "suma_area"]].fillna(0)
tabla.to_csv(RES / "tabla_mapas_departamento.csv", index_label="codigo_dane", encoding="utf-8-sig")
print(f"Suma de registros en la tabla: {int(tabla['n_registros'].sum())}")
print(f"Suma de área en la tabla (hectáreas): {tabla['suma_area'].sum():,.1f}")  # esperado 2,163,299.3

# 2. Límites departamentales (shapefile del DANE) ----------------------------
archivos = sorted(CARPETA_LIMITES.rglob("*.shp")) if CARPETA_LIMITES.exists() else []
if not archivos:
    raise SystemExit(
        "\nNo encontré ningún .shp en la carpeta limites_dane/.\n"
        "Descarga los límites departamentales del DANE (Marco Geoestadístico "
        "Nacional), descomprímelos ahí y vuelve a correr el script."
    )
elegido = next((p for p in archivos if "dpto" in p.name.lower()), archivos[0])
print(f"\nLímites usados: {elegido.name}")

sf = shapefile.Reader(str(elegido), encoding="latin-1")
campos = [f[0] for f in sf.fields[1:]]
campo_codigo = next((c for c in campos if c.lower() == "dpto_ccdgo"), None)
if campo_codigo is None:
    campo_codigo = next(
        (c for c in campos if "dpto" in c.lower() and ("cdgo" in c.lower() or "cod" in c.lower())),
        None,
    )
if campo_codigo is None:
    raise SystemExit(f"\nNo encontré el campo con el código del departamento. Campos: {campos}")


def a_ruta(forma):
    pts = [tuple(p) for p in forma.points]
    inicios = list(forma.parts) + [len(pts)]
    verts, codes = [], []
    for i in range(len(inicios) - 1):
        anillo = pts[inicios[i]:inicios[i + 1]]
        if len(anillo) < 3:
            continue
        verts += anillo + [anillo[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(anillo) - 1) + [MPath.CLOSEPOLY]
    return MPath(verts, codes), pts


formas = []
for sr in sf.iterShapeRecords():
    if len(sr.shape.points) == 0:
        continue
    rec = dict(zip(campos, list(sr.record)))
    codigo = str(rec[campo_codigo]).strip().zfill(2)
    ruta, pts = a_ruta(sr.shape)
    formas.append((codigo, ruta, pts))

if len(formas) > 40:
    print(f"AVISO: el archivo tiene {len(formas)} polígonos; parece municipal. "
          "Usa el departamental (MGN_DPTO_POLITICO).")

codigos_mapa = {c for c, _, _ in formas}
print(f"Polígonos leídos: {len(formas)}")
faltan = sorted(set(tabla.index) - codigos_mapa)
if faltan:
    print(f"AVISO: códigos de la base sin polígono: {faltan}")

todos = np.array([p for _, _, pts in formas for p in pts])
xmin, ymin = todos.min(axis=0)
xmax, ymax = todos.max(axis=0)
pad_x, pad_y = (xmax - xmin) * 0.02, (ymax - ymin) * 0.02


# 3. Dibujo -----------------------------------------------------------------
def dibujar(valores, titulo, etiqueta_barra, archivo, nota_extra, n_etiquetas=5):
    # Se recorta el extremo casi blanco de la paleta para que los valores
    # bajos no se confundan con el fondo de la figura.
    cmap = LinearSegmentedColormap.from_list(
        "YlOrRd_recortada", plt.get_cmap("YlOrRd")(np.linspace(0.18, 1, 256)))
    norm = Normalize(vmin=0, vmax=max(float(valores.max()), 1.0))
    fig, ax = plt.subplots(figsize=(6.5, 8.4))
    for codigo, ruta, _ in formas:
        v = valores.get(codigo, 0)
        color = "#d9d9d9" if (pd.isna(v) or v <= 0) else cmap(norm(v))
        ax.add_patch(PathPatch(ruta, facecolor=color, edgecolor="#666666", linewidth=0.4))

    # Etiquetas de los mayores
    for codigo in valores.nlargest(n_etiquetas).index:
        candidatos = [pts for c, _, pts in formas if c == codigo]
        if not candidatos:
            continue
        pts = np.array(max(candidatos, key=len))
        cx, cy = (pts.min(axis=0) + pts.max(axis=0)) / 2
        nombre = str(tabla.loc[codigo, "departamento"]).title()
        ax.text(cx, cy, f"{nombre}\n{valores[codigo]:,.0f}", ha="center", va="center",
                fontsize=6.5, bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.75, lw=0))

    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{titulo}\nescenario principal, {periodo}", fontsize=11)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02,
                 label=etiqueta_barra)
    partes = [
        "Fuente de los registros: IDEAM, consolidado en incendios_consolidados_auditados.csv.",
        f"Límites: DANE, Marco Geoestadístico Nacional. Gris = sin registros. {nota_extra}",
        "Sin denominador: no se ajusta por superficie del departamento.",
    ]
    nota = "\n".join(textwrap.fill(p, 95) for p in partes)  # parte las líneas largas
    fig.text(0.5, 0.01, nota, ha="center", va="bottom", fontsize=7, color="#222222")
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(RES / archivo, dpi=150)
    plt.close(fig)


dibujar(
    tabla["n_registros"],
    "Registros de incendios de la cobertura vegetal por departamento",
    "Número de registros",
    "mapa_registros_departamento.png",
    "Cuenta las filas del escenario principal que tienen departamento.",
    n_etiquetas=3,
)
dibujar(
    tabla["suma_area"],
    "Área acumulada reportada por departamento (hectáreas)",
    "Suma de area_total (hectáreas)",
    "mapa_area_departamento.png",
    "Solo registros con área mayor que cero.",
)

print("\nTop 5 por número de registros:")
print(tabla.nlargest(5, "n_registros")[["departamento", "n_registros"]].to_string())
print("\nTop 5 por suma de área:")
print(tabla.nlargest(5, "suma_area")[["departamento", "suma_area"]].round(1).to_string())
print("\nGuardado: mapa_registros_departamento.png, mapa_area_departamento.png, tabla_mapas_departamento.csv")
