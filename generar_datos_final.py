import pandas as pd
import geopandas as gpd
import os
import numpy as np

# ==========================================
# 📍 CONFIGURACIÓN DEL MUNICIPIO OBJETIVO
# ==========================================
# CAMBIA ESTE CÓDIGO POR EL DEL MUNICIPIO QUE QUIERAS
# Ejemplos: '032' (Catemaco), '087' (Xalapa), '118' (Orizaba), '193' (Veracruz)
MUNICIPIO_OBJETIVO = '032' 

# ==========================================
# RUTAS
# ==========================================
PATH_SHP_URB = "data/mapas/30m.shp"
PATH_SHP_RUR = "data/mapas/30l.shp"
PATH_SHP_POL = "data/mapas/SECCION.shp"
PATH_CSV_URB = "data/tablas/conjunto_de_datos_ageb_urbana_30_cpv2020.csv"
PATH_CSV_RUR = "data/tablas/iter_veracruz_2020.csv"
PATH_CSV_POL = "data/tablas/Municipal_2025.csv"

if not os.path.exists("output"): os.makedirs("output")

print(f"🚀 INICIANDO PROCESO SITS PARA EL MUNICIPIO: {MUNICIPIO_OBJETIVO}...")

def limpiar(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

# VARIABLES COMPLETAS
VARS_CENSO = [
    'POBTOT', 'POBFEM', 'POBMAS', 
    'POB0_14', 'POB15_64', 'P_60YMAS', 'P_65YMAS',
    'P3YM_HLI', 'POB_AFRO', 'PCON_DISC',
    'HOGJEF_F', 
    'TVIVPARHAB', 'VPH_PISOTI', 'VPH_NODREN', 'VPH_S_ELEC', 'VPH_AGUAFV', 
    'VPH_REFRI', 'VPH_LAVAD', 'VPH_AUTOM', 'VPH_PC',
    'PDER_SS', 'P_15YMAS', 'P15YM_AN', 'P15YM_SE'
]

def procesar_indicadores(df):
    for c in ['POBTOT', 'TVIVPARHAB', 'P_15YMAS']:
        if c in df.columns: df[c] = df[c].replace(0, 1)

    def g(col): return df[col] if col in df.columns else 0

    df['CAR_EDU_20'] = (g('P15YM_AN') + g('P15YM_SE')) / df['P_15YMAS']
    df['CAR_SALUD_20'] = 1 - (g('PDER_SS') / df['POBTOT'])
    df['CAR_VIV_20'] = g('VPH_PISOTI') / df['TVIVPARHAB']
    df['CAR_SERV_20'] = (g('VPH_AGUAFV') + g('VPH_NODREN') + g('VPH_S_ELEC')) / 3 / df['TVIVPARHAB']
    df['CAR_ALIM_20'] = 1 - (g('VPH_REFRI') / df['TVIVPARHAB'])
    
    activos = (g('VPH_REFRI') + g('VPH_LAVAD') + g('VPH_AUTOM') + g('VPH_PC'))
    df['CAR_POBREZA_20'] = 1 - (activos / (4 * df['TVIVPARHAB']))
    
    cols = ['CAR_EDU_20', 'CAR_SALUD_20', 'CAR_VIV_20', 'CAR_SERV_20', 'CAR_ALIM_20', 'CAR_POBREZA_20']
    for c in cols: df[c] = df[c].clip(0, 1)
    
    df['SITS_INDEX'] = df[cols[:5]].mean(axis=1)
    return df

# PROCESAMIENTO GEOGRÁFICO
def procesar_geo(shp_path, csv_path, tipo, filtro_mun):
    print(f"\n📂 Procesando {tipo} para MUN {filtro_mun}...")
    try:
        shp = gpd.read_file(shp_path)
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as e:
        print(f"   ❌ Error archivo: {e}")
        return None

    # FILTRO DINÁMICO POR MUNICIPIO
    if tipo == 'Urbano':
        df = df[(df['MUN'] == filtro_mun) & (df['MZA'] != '000')]
        # Detectar nombre del municipio automáticamente
        nombre_mun = df['NOM_MUN'].iloc[0] if not df.empty else "Desconocido"
        df['CVEGEO'] = df['ENTIDAD']+df['MUN']+df['LOC']+df['AGEB']+df['MZA']
    else:
        df = df[df['MUN'].str.endswith(filtro_mun)]
        nombre_mun = df['NOM_MUN'].iloc[0] if not df.empty else "Desconocido"
        df['CVEGEO'] = df['ENTIDAD']+df['MUN']+df['LOC']

    print(f"   ℹ️ Municipio Detectado: {nombre_mun}")

    # Limpieza
    if 'POB_FEM' in df.columns: df.rename(columns={'POB_FEM':'POBFEM'}, inplace=True)
    if 'POB_MAS' in df.columns: df.rename(columns={'POB_MAS':'POBMAS'}, inplace=True)
    if 'VPH_LAVADORA' in df.columns: df.rename(columns={'VPH_LAVADORA':'VPH_LAVAD'}, inplace=True)
    
    df = limpiar(df, VARS_CENSO)
    df = procesar_indicadores(df)
    
    # Merge
    final = shp.merge(df, on='CVEGEO', how='inner')
    final['TIPO'] = tipo
    final['NOM_MUN_OFICIAL'] = nombre_mun # Guardamos el nombre para que la App lo lea
    
    # Variables App
    def safe(col): return final[col] if col in final.columns else 0

    final['P20_TOT'] = safe('POBTOT')
    final['P20_FEM'] = safe('POBFEM')
    final['P20_MAS'] = safe('POBMAS')
    final['P20_IND'] = safe('P3YM_HLI')
    final['P20_AFRO'] = safe('POB_AFRO')
    final['P20_DISC'] = safe('PCON_DISC')
    final['P20_JEFAS'] = safe('HOGJEF_F')
    final['P20_NINOS'] = safe('POB0_14')
    final['P20_MAYORES'] = safe('P_60YMAS')
    
    cols_pob = [c for c in final.columns if c.startswith('P20_')]
    for c in cols_pob:
        final[c.replace('P20_', 'P25_')] = final[c] * 1.05
        
    return final

# EJECUCIÓN
u_final = procesar_geo(PATH_SHP_URB, PATH_CSV_URB, 'Urbano', MUNICIPIO_OBJETIVO)
if u_final is not None:
    # Usamos el nombre detectado del municipio
    nombre_mpio = u_final['NOM_MUN_OFICIAL'].iloc[0]
    u_final['NOM_LOC'] = nombre_mpio + " (Cabecera)" # Para que se vea bonito en el filtro
    
    u_final['CVE_AGEB'] = u_final['AGEB_y'] if 'AGEB_y' in u_final.columns else u_final.get('AGEB', 'SN')
    u_final['CVE_MZA'] = u_final['MZA_y'] if 'MZA_y' in u_final.columns else u_final.get('MZA', '000')
    u_final.to_crs(epsg=4326).to_file("output/sits_capa_urbana.geojson", driver='GeoJSON')
    print("   ✅ Urbano listo.")

r_final = procesar_geo(PATH_SHP_RUR, PATH_CSV_RUR, 'Rural', MUNICIPIO_OBJETIVO)
if r_final is not None:
    r_final['NOM_LOC'] = r_final['NOMGEO']
    r_final['CVE_AGEB'] = 'RURAL'
    r_final.to_crs(epsg=4326).to_file("output/sits_capa_rural.geojson", driver='GeoJSON')
    print("   ✅ Rural listo.")

# ELECTORAL (Filtramos por extensión geográfica aproximada o cargamos todo)
# Nota: La capa electoral es por sección. Para hacerlo dinámico exacto necesitaríamos
# un catálogo de SECCION vs MUNICIPIO. Por ahora, generamos la capa pero el mapa
# se centrará donde estén los datos urbanos.
print("\n📂 Procesando Electoral...")
try:
    p_shp = gpd.read_file(PATH_SHP_POL)
    p_csv = pd.read_csv(PATH_CSV_POL)
    
    # Filtrar secciones que corresponden al municipio (Cruce espacial idealmente, 
    # pero aquí usaremos el bounding box de lo urbano para no cargar todo el estado)
    if u_final is not None:
        minx, miny, maxx, maxy = u_final.total_bounds
        # Filtro simple: Secciones dentro de la caja del municipio (optimización)
        p_shp = p_shp.cx[minx:maxx, miny:maxy]
    
    p_shp['SECCION'] = p_shp['SECCION'].astype(int)
    p_csv['seccion'] = p_csv['seccion'].astype(int)
    p_final = p_shp.merge(p_csv.groupby('seccion')[['morena','pan','pri','mc']].sum().reset_index(), left_on='SECCION', right_on='seccion')
    p_final['GANADOR'] = p_final[['morena','pan','pri','mc']].idxmax(axis=1)
    p_final.to_crs(epsg=4326).to_file("output/sits_capa_politica.geojson", driver='GeoJSON')
    print("   ✅ Electoral listo (Recortado a la zona).")
except Exception as e:
    print(f"   ⚠️ Error Electoral: {e}")

print(f"\n🏁 SITS GENERADO PARA EL MUNICIPIO {MUNICIPIO_OBJETIVO}.")
