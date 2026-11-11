"""
mapas_densidad.py  (Paso 2)

Dibuja dos mapas por departamento:
  1) registros por 1.000 km2
  2) hectareas por km2 (area_total, en hectareas)

Lee:  resultados/densidad_departamental.csv  (salida de densidad_departamentos.py)
      limites_dane/MGN2025_DPTO_POLITICO/MGN_ADM_DPTO_POLITICO.shp
Guarda dos PNG en resultados/.

Uso (dentro de entrega_incendios, con el .venv activo):
    python mapas_densidad.py
"""
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile  # pyshp
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

BASE = Path(__file__).resolve().parent
CSV = BASE / "resultados" / "densidad_departamental.csv"
SHP = BASE / "limites_dane" / "MGN2025_DPTO_POLITICO" / "MGN_ADM_DPTO_POLITICO.shp"
CODIGO_SAN_ANDRES = "88"

# ---------- datos ----------
tabla = pd.read_csv(CSV, dtype={"codigo_dane": str})
tabla["codigo_dane"] = tabla["codigo_dane"].str.zfill(2)
print("Departamentos en la tabla:", len(tabla), "(esperado: 33)")

try:
    sf = shapefile.Reader(str(SHP), encoding="utf-8", encodingErrors="replace")
except TypeError:
    sf = shapefile.Reader(str(SHP), encoding="utf-8")
campos = [f[0] for f in sf.fields[1:]]
i_cod = [i for i, c in enumerate(campos) if "ccdgo" in c.lower()][0]

formas = []  # (codigo, shape)
for sr in sf.shapeRecords():
    formas.append((str(sr.record[i_cod]).zfill(2), sr.shape))
print("Poligonos leidos:", len(formas), "(esperado: 33)")


def camino(shape):
    """Une todos los anillos del departamento en un solo trazado."""
    pts = np.array(shape.points)
    partes = list(shape.parts) + [len(pts)]
    vertices, codigos = [], []
    for a, b in zip(partes[:-1], partes[1:]):
        anillo = pts[a:b]
        if len(anillo) < 3:
            continue
        vertices.extend(anillo.tolist())
        codigos.extend([MPath.MOVETO] + [MPath.LINETO] * (len(anillo) - 2) + [MPath.CLOSEPOLY])
    return MPath(vertices, codigos)


# los grandes primero, para que Bogota quede encima de Cundinamarca
formas.sort(key=lambda x: -(x[1].bbox[2] - x[1].bbox[0]) * (x[1].bbox[3] - x[1].bbox[1]))


def dibujar(columna, titulo, etiqueta, archivo, nota):
    valores = tabla.set_index("codigo_dane")[columna]
    bordes = np.unique(np.quantile(valores.values, [0, 0.2, 0.4, 0.6, 0.8, 1.0]))
    bordes[-1] = bordes[-1] * 1.0001
    n_clases = len(bordes) - 1
    # se salta el amarillo casi blanco para que ninguna clase se confunda con el fondo
    cmap = ListedColormap(plt.cm.YlOrRd(np.linspace(0.18, 1.0, n_clases)))
    norm = BoundaryNorm(bordes, cmap.N)

    fig, ax = plt.subplots(figsize=(7, 8))
    ax_sa = fig.add_axes([0.10, 0.14, 0.16, 0.16])  # recuadro de San Andres (zona vacia, abajo a la izquierda)

    for codigo, shape in formas:
        if codigo not in valores.index:
            continue
        color = cmap(norm(valores[codigo]))
        patch = dict(facecolor=color, edgecolor="#666666", linewidth=0.5)
        if codigo == CODIGO_SAN_ANDRES:
            ax_sa.add_patch(PathPatch(camino(shape), **patch))
            x0, y0, x1, y1 = shape.bbox
            ax_sa.set_xlim(x0 - 0.1, x1 + 0.1)
            ax_sa.set_ylim(y0 - 0.1, y1 + 0.1)
        else:
            ax.add_patch(PathPatch(camino(shape), **patch))

    ax.set_xlim(-79.5, -66.5)
    ax.set_ylim(-4.5, 13.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax_sa.set_xticks([])
    ax_sa.set_yticks([])
    ax_sa.set_title("San Andrés\n(%.1f)" % valores[CODIGO_SAN_ANDRES], fontsize=8)

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02, ticks=bordes)
    cb.ax.set_yticklabels(["%.1f" % b for b in bordes])
    cb.set_label(etiqueta, fontsize=9)

    ax.set_title(titulo, fontsize=12)
    fig.text(0.02, 0.0, textwrap.fill(nota, 100), fontsize=7.5, va="top")
    fig.savefig(BASE / "resultados" / archivo, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Guardado:", archivo, "| minimo %.2f | maximo %.2f" % (valores.min(), valores.max()))
    print("  cortes de las clases:", ["%.1f" % b for b in bordes])


nota_comun = (
    "Fuente: IDEAM, incendios de cobertura vegetal 2002-2025 (escenario principal, "
    "registros con departamento). Límites y superficie: DANE MGN 2025 (dpto_narea, km²; en los metadatos del DANE: Área departamento (Km2)). "
    "Clases por quintiles. Totales de todos los años."
)

dibujar(
    "registros_por_1000km2",
    "Registros de incendios por 1.000 km², 2002-2025",
    "Registros por 1.000 km²",
    "mapa_registros_por_1000km2.png",
    nota_comun,
)
dibujar(
    "hectareas_por_km2",
    "Hectáreas reportadas por km², 2002-2025",
    "Hectáreas por km²",
    "mapa_area_por_km2.png",
    nota_comun + " area_total está en hectáreas (IDEAM, radicado 20265000183351, 26 oct 2026).",
)
