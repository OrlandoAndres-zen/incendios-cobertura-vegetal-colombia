"""Análisis reproducible de los archivos IDEAM adjuntos. Python >=3.10.
Ejecutar: python analizar_incendios.py
Los duplicados candidatos se marcan, no se eliminan en el análisis principal.
No transforma coordenadas ambiguas ni inventa áreas o meses sin reporte.
"""
from pathlib import Path
from datetime import datetime, date
import json, unicodedata, hashlib
import numpy as np
import pandas as pd
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'resultados'
OUT.mkdir(exist_ok=True)
COLS = ['anio','mes_original','dia_original','departamento','municipio','vereda','predio','area_protegida','latitud_original','longitud_original','elevacion','tipo_copa','tipo_superficial','tipo_subterraneo','tipo_mixto','tipo_otro','causa_quema','causa_negligencia','causa_intencional','causa_accidental','causa_reactivacion','causa_otra','bosque_denso','bosque_intervenido','bosque_plantado','bosque_seco','cultivos','paramo','sabana_pastizal','pastos_manejados','rastrojo','vegetacion_seca','cobertura_indeterminada','area_total_original']
MONTHS = dict(zip(['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'],range(1,13)))
def norm(x):
    if x is None or pd.isna(x): return ''
    return ' '.join(unicodedata.normalize('NFKD',str(x)).encode('ascii','ignore').decode().upper().split())
def number(x):
    if isinstance(x,(int,float)) and np.isfinite(x):return float(x)
    s=str(x).strip().replace(' ','')
    # No adivinar separadores de miles. Se acepta sólo decimal inequívoco.
    if ',' in s and '.' in s:return np.nan
    try:return float(s.replace(',','.'))
    except (ValueError,TypeError):return np.nan
def month(x):
    s=norm(x)
    if s in MONTHS:return MONTHS[s]
    n=number(x)
    return int(n) if np.isfinite(n) and n.is_integer() and 1<=n<=12 else np.nan
rows=[]
inventory=[]
for f in sorted((ROOT/'originales').glob('*.xlsx')):
    w=openpyxl.load_workbook(f,read_only=True,data_only=True)
    for sh in w:
        if not sh.title.strip().startswith('BD_ICV'):continue
        start=False; count=0
        for i,row in enumerate(sh.values,1):
            if len(row)>1 and norm(row[1])=='ANO':start=True;continue
            if not start:continue
            vals=list(row[1:35]);vals += [None]*(34-len(vals))
            y=number(vals[0])
            if not np.isfinite(y) or not y.is_integer() or not 2002<=y<=2025:continue
            if not norm(vals[3]) and not norm(vals[4]):continue
            item=dict(zip(COLS,vals));item.update(archivo=f.name,hoja=sh.title,fila_excel=i)
            rows.append(item);count+=1
        inventory.append({'archivo':f.name,'hoja':sh.title,'registros':count,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    w.close()
d=pd.DataFrame(rows)
d['anio']=d.anio.astype(int)
for c in ['departamento','municipio']:d[c+'_original']=d[c];d[c]=d[c].map(norm)
# Sólo unificar nombres departamentales inequívocos; otras variantes se auditan.
d['departamento']=d.departamento.replace({'BOGOTA D.C.':'BOGOTA D.C.','BOGOTA D. C.':'BOGOTA D.C.','BOGOTA':'BOGOTA D.C.','BOGOTA DC':'BOGOTA D.C.','BOGOTA, D.C.':'BOGOTA D.C.','SAN ANDRES':'ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA'})
d['mes_declarado']=d.mes_original.map(month)
dates=pd.to_datetime(d.dia_original.where(d.dia_original.map(lambda x:isinstance(x,(datetime,date)))),errors='coerce')
d['fecha']=dates
d['fecha_conflicto_anio']=dates.notna() & dates.dt.year.ne(d.anio)
d['fecha_conflicto_mes']=dates.notna() & d.mes_declarado.notna() & dates.dt.month.ne(d.mes_declarado)
d['mes']=d.mes_declarado
recover=d.mes.isna() & dates.notna() & ~d.fecha_conflicto_anio
d.loc[recover,'mes']=dates.dt.month[recover]
d['area_total']=d.area_total_original.map(number)
d['area_positiva']=d.area_total.gt(0)&np.isfinite(d.area_total)
d['coordenadas_informadas']=d.latitud_original.map(norm).ne('') & d.longitud_original.map(norm).ne('')
# Sólo coordenadas ya numéricas decimales con signo y rango amplio de Colombia.
lat=d.latitud_original.map(number);lon=d.longitud_original.map(number)
d['coordenadas_decimales_plausibles']=lat.between(-4.5,13.6)&lon.between(-82,-66)
d['latitud_decimal']=lat.where(d.coordenadas_decimales_plausibles)
d['longitud_decimal']=lon.where(d.coordenadas_decimales_plausibles)
d['usar_principal']=~((d.anio==2010)&d.archivo.str.contains('2002_2010'))
# Huella de los 34 valores, conservando las ubicaciones locales y las coberturas.
keys=d[COLS].map(norm) if hasattr(d[COLS],'map') else d[COLS].applymap(norm)
d['duplicado_exacto_candidato']=keys.duplicated(keep=False)
d['duplicado_exacto_posterior']=keys.duplicated(keep='first')
d.to_csv(OUT/'incendios_consolidados_auditados.csv',index=False)
pd.DataFrame(inventory).to_csv(OUT/'inventario_fuentes.csv',index=False)
d[d.duplicado_exacto_candidato].to_csv(OUT/'duplicados_para_revision.csv',index=False)
d[d.fecha_conflicto_anio|d.fecha_conflicto_mes|d.mes.isna()|~d.area_positiva].to_csv(OUT/'registros_para_revision.csv',index=False)
a=d[d.usar_principal].copy()
# La sensibilidad deduplica dentro del escenario principal, no contra filas excluidas.
akey=a[COLS].map(norm) if hasattr(a[COLS],'map') else a[COLS].applymap(norm)
a['duplicado_principal_posterior']=akey.duplicated()
annual=a.groupby('anio').agg(registros=('anio','size'),con_area_positiva=('area_positiva','sum'),area_suma=('area_total',lambda s:s[s>0].sum(min_count=1)),area_mediana=('area_total',lambda s:s[s>0].median()),con_mes=('mes','count'),con_coordenadas=('coordenadas_informadas','sum'),coords_decimales_plausibles=('coordenadas_decimales_plausibles','sum'),mes_maximo_observado=('mes','max'))
annual['registros_sin_duplicados_exactos']=a[~a.duplicado_principal_posterior].groupby('anio').size()
annual.to_csv(OUT/'resumen_anual.csv')
monthly=a.dropna(subset=['mes']).groupby(['anio','mes']).agg(registros=('anio','size'),area_suma=('area_total',lambda s:s[s>0].sum(min_count=1)),con_area_positiva=('area_positiva','sum'))
# Meses ausentes son NA, porque no se ha establecido cobertura de reporte.
monthly=monthly.reindex(pd.MultiIndex.from_product([range(2002,2026),range(1,13)],names=['anio','mes']))
monthly['estado_reporte']=np.where(monthly.registros.isna(),'SIN_REGISTROS_COBERTURA_NO_VERIFICADA','CON_REGISTROS')
monthly.reset_index().to_csv(OUT/'serie_mensual.csv',index=False)
dept=a.groupby('departamento').agg(registros=('anio','size'),area_suma=('area_total',lambda s:s[s>0].sum(min_count=1)),con_area_positiva=('area_positiva','sum')).sort_values('registros',ascending=False)
dept.to_csv(OUT/'resumen_departamental.csv')
a.groupby(['departamento','municipio']).agg(registros=('anio','size'),con_area_positiva=('area_positiva','sum'),area_suma=('area_total',lambda s:s[s>0].sum(min_count=1))).sort_values('registros',ascending=False).to_csv(OUT/'resumen_municipal.csv')
area=a.loc[a.area_positiva,'area_total'].sort_values()
summary={'registros_fuentes':len(d),'registros_principal':len(a),'excluidos_solapamiento_2010':int((~d.usar_principal).sum()),'sin_mes':int(a.mes.isna().sum()),'conflicto_fecha_anio':int(a.fecha_conflicto_anio.sum()),'conflicto_fecha_mes':int(a.fecha_conflicto_mes.sum()),'area_positiva_n':len(area),'area_cero_n':int(a.area_total.eq(0).sum()),'area_negativa_n':int(a.area_total.lt(0).sum()),'area_no_numerica_n':int(a.area_total.isna().sum()),'area_percentiles':{str(p):float(area.quantile(p)) for p in [.25,.5,.75,.9,.95,.99]},'area_maxima':float(area.max()),'area_suma':float(area.sum()),'fraccion_area_mayor_1pct':float(area.tail(int(np.ceil(len(area)*.01))).sum()/area.sum()),'con_coordenadas_informadas':int(a.coordenadas_informadas.sum()),'con_coords_decimales_plausibles':int(a.coordenadas_decimales_plausibles.sum()),'duplicados_exactos_posteriores_principal':int(a.duplicado_principal_posterior.sum()),'unidad_area':'UNIDAD DE AREA TOTAL PENDIENTE DE CONFIRMACION DOCUMENTAL'}
a.nlargest(30,'area_total').to_csv(OUT/'mayores_areas_para_revision.csv',index=False)
d[d.anio.eq(2010)].groupby('archivo').agg(registros=('anio','size'),area_suma=('area_total',lambda s:s[s>0].sum(min_count=1))).to_csv(OUT/'auditoria_solapamiento_2010.csv')
# ONI ERSSTv5: corte fijo transcrito de NOAA CPC, incluido en el paquete.
oni=pd.read_csv(ROOT/'oni_noaa_v5.csv')
sign=np.where(oni.oni>=.5,1,np.where(oni.oni<=-.5,-1,0))
phase=np.full(len(oni),'Neutral',dtype=object)
start=0
for end in range(1,len(sign)+1):
    if end==len(sign) or sign[end]!=sign[start]:
        if sign[start]!=0 and end-start>=5:phase[start:end]='El Nino' if sign[start]>0 else 'La Nina'
        start=end
oni['fase_episodio']=phase
oni['umbral_sin_persistencia']=np.where(sign>0,'Calido',np.where(sign<0,'Frio','Neutral'))
joined=monthly.reset_index().merge(oni,on=['anio','mes'],how='left',validate='one_to_one')
joined.to_csv(OUT/'serie_mensual_con_ONI.csv',index=False)
# Comparación descriptiva, no inferencia: mismo año-mes; evitar 2025 sin cierre.
comparison=joined[joined.anio<=2024].groupby('fase_episodio').agg(meses_calendario=('mes','size'),meses_con_registros=('registros','count'),registros=('registros','sum'),promedio_mensual_observado=('registros','mean'),mediana_mensual_observada=('registros','median'))
comparison.to_csv(OUT/'comparacion_ENSO_descriptiva.csv')
event_enso=a.merge(oni,on=['anio','mes'],how='left',validate='many_to_one')
event_enso[event_enso.anio<=2024].groupby('fase_episodio').agg(registros=('anio','size'),n_area=('area_positiva','sum'),mediana_area=('area_total',lambda s:s[s>0].median()),p90_area=('area_total',lambda s:s[s>0].quantile(.9))).to_csv(OUT/'tamanos_por_ENSO_descriptivos.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(2,2,figsize=(13,9))
annual.registros.plot.bar(ax=ax[0,0],color='#197278');ax[0,0].set_title('Registros por año · 2025 sujeto a cierre');ax[0,0].set_ylabel('Filas de eventos reportados')
season=a[a.anio<=2024].groupby('mes').size().reindex(range(1,13))
season.plot.bar(ax=ax[0,1],color='#197278');ax[0,1].set_title('Estacionalidad acumulada · 2002–2024');ax[0,1].set_xlabel('Mes');ax[0,1].set_ylabel('Registros')
x=area.to_numpy();y=(len(x)-np.arange(len(x)))/len(x)
ax[1,0].loglog(x,y,color='#a64b2a');ax[1,0].set_title('Cola empírica del tamaño · áreas positivas');ax[1,0].set_xlabel('Área total (unidad por confirmar)');ax[1,0].set_ylabel('Fracción con área ≥ x');ax[1,0].grid(alpha=.2)
dept.registros.head(10).sort_values().plot.barh(ax=ax[1,1],color='#197278');ax[1,1].set_title('Concentración de reportes por departamento');ax[1,1].set_xlabel('Registros')
fig.suptitle('Incendios de cobertura vegetal en Colombia · exploración del archivo adjunto',fontsize=15)
fig.tight_layout();fig.savefig(OUT/'exploracion.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(12,4))
p=joined[joined.anio<=2024].copy();p['periodo']=pd.to_datetime(dict(year=p.anio,month=p.mes,day=1))
ax.plot(p.periodo,p.registros,color='#197278',label='Registros mensuales')
ax2=ax.twinx();ax2.plot(p.periodo,p.oni,color='#a64b2a',alpha=.7,label='ONI ERSSTv5');ax2.axhline(.5,color='grey',lw=.5);ax2.axhline(-.5,color='grey',lw=.5)
ax.set_ylabel('Registros');ax2.set_ylabel('ONI (°C)');ax.set_title('Incendios y ONI · coincidencia temporal descriptiva, sin ajuste')
fig.tight_layout();fig.savefig(OUT/'serie_ONI.png',dpi=170);plt.close(fig)
(OUT/'resumen_auditoria.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('\nANUAL\n',annual.to_string());print('\nDEPARTAMENTOS\n',dept.head(10).to_string());print('\nENSO\n',comparison.to_string())
