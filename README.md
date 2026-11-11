# Incendios de cobertura vegetal en Colombia: tiempo, tamaño y territorio

Código del artículo del mismo nombre (borrador, noviembre de 2026).

**Autores:** Julián Andrés Maestre Santos y Orlando Andres Buitrago Reales.
Estadística, Universidad Nacional de Colombia, sede La Paz. Asignatura: Geometría Vectorial y Analítica.

## De qué trata

Se describe cómo varían la frecuencia registrada, el tamaño reportado (en hectáreas) y la concentración territorial de los incendios de cobertura vegetal registrados por el IDEAM entre 2002 y 2025, y cómo se asocian con las fases de ENSO y con la lluvia y la temperatura locales. El enfoque es descriptivo y de asociación: no se atribuyen causas.

## Carpetas

| Carpeta | Qué contiene |
| :-- | :-- |
| `limpieza_y_auditoria/` | Scripts de lectura de los Excel, limpieza, revisión de repeticiones, fechas, coordenadas y registros dudosos. Son de los dos autores. |
| `tamano_y_territorio/` | Scripts del análisis del tamaño de los registros (por región y fase ENSO, en la misma estación), de la concentración territorial por departamento y de los mapas. |
| `frecuencia_y_clima/` | Scripts del análisis de frecuencia por departamento y mes y su relación con ENSO, la lluvia y la temperatura. |
| `datos/` | Solo un texto con las fuentes de los datos. No se incluyen los datos. |

## Los datos no están en este repositorio

Los registros son del IDEAM, que indica que la base se usa bajo responsabilidad del usuario y que está prohibida su comercialización. Por eso no se publican los archivos originales ni la base completa. Para reproducir el análisis, quien lo desee debe solicitar los registros al IDEAM. Las fuentes y las versiones están en `datos/LEER.md` y en la sección de referencias del artículo.

## Cómo reproducirlo

1. Consigue los tres archivos de Excel de los registros 2002-2010, 2010-2020 y 2021-2025 (ver arriba).
2. Crea una carpeta de trabajo con una subcarpeta `originales/` y pon allí los tres archivos.
3. Instala las dependencias en un entorno virtual de Python.
4. Copia los scripts a la carpeta de trabajo y córrelos desde allí. Los scripts usan rutas relativas a su propia carpeta y escriben en `resultados/`.
5. Empieza por `limpieza_y_auditoria/analizar_incendios.py`, que genera la base auditada. Después corre los demás.

## Decisiones importantes

- El año 2010 está en dos archivos del IDEAM. En el escenario principal se usa una sola copia (45.166 registros de 47.527 filas).
- Nada se elimina sin evidencia: los registros dudosos se marcan y se mantienen, y los resultados se repiten sin ellos como prueba de sensibilidad.
- La unidad del área es la hectárea, según el IDEAM.

## Requisitos

Python 3 con pandas, NumPy, Matplotlib, GeoPandas y openpyxl (análisis de tamaño y territorio) y SciPy y statsmodels (frecuencia y clima). Las versiones exactas están en la sección de metodología del artículo.

## Licencia

[Por definir. Se aplica solo al código; los datos del IDEAM tienen sus propias condiciones.]
