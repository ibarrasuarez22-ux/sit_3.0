import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(layout="wide", page_title="SITS Catemaco Pro", page_icon="🦅")

st.markdown("""
<style>
    .kpi-card { background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #e74c3c; text-align: center; margin-bottom: 10px; }
    .kpi-title { font-size: 14px; color: #7f8c8d; text-transform: uppercase; font-weight: 600; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #2c3e50; margin-top: 5px; }
    .filter-container { background-color: #f1f2f6; padding: 15px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ SITS: Sistema de Inteligencia Territorial")
st.markdown("**Diagnóstico Estratégico Municipal 2025**")

# ==========================================
# 2. CARGA DE DATOS
# ==========================================
@st.cache_data
def cargar_datos():
    f_urb = "output/sits_capa_urbana.geojson"
    f_rur = "output/sits_capa_rural.geojson"
    f_pol = "output/sits_capa_politica.geojson"
    
    u = gpd.read_file(f_urb) if os.path.exists(f_urb) else None
    r = gpd.read_file(f_rur) if os.path.exists(f_rur) else None
    p = gpd.read_file(f_pol) if os.path.exists(f_pol) else None
    
    if u is not None:
        u['TIPO'] = 'Urbano'; u['NOM_LOC'] = 'Catemaco'
        if 'CVE_AGEB' not in u.columns: u['CVE_AGEB'] = u['AGEB'] if 'AGEB' in u.columns else 'SN'
    if r is not None:
        r['TIPO'] = 'Rural'; r['NOM_LOC'] = r['NOMGEO']; r['CVE_AGEB'] = 'RURAL'
    return u, r, p

gdf_u, gdf_r, gdf_p = cargar_datos()

if gdf_u is None or gdf_r is None:
    st.error("🚨 ERROR: Ejecuta 'python3 generar_datos_final.py' primero.")
    st.stop()

# ==========================================
# 3. FILTROS LATERALES
# ==========================================
with st.sidebar:
    st.header("🎛️ Filtros Generales")
    st.info("💡 **¿Para qué sirve?**: Estos filtros afectan a TODAS las pestañas. Selecciona una zona geográfica específica para analizarla en detalle.")
    
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    locs = sorted(list(set(gdf_u['NOM_LOC'].unique()) | set(gdf_r['NOM_LOC'].unique())))
    sel_loc = st.selectbox("📍 Localidad:", ["TODO EL MUNICIPIO"] + locs)
    
    du = gdf_u.copy()
    dr = gdf_r.copy()
    
    if sel_loc != "TODO EL MUNICIPIO":
        du = du[du['NOM_LOC'] == sel_loc]
        dr = dr[dr['NOM_LOC'] == sel_loc]
    
    sel_ageb = "TODAS"
    if not du.empty:
        agebs = sorted(du['CVE_AGEB'].unique())
        sel_ageb = st.selectbox("🏘️ AGEB (Urbano):", ["TODAS"] + agebs)
        if sel_ageb != "TODAS": du = du[du['CVE_AGEB'] == sel_ageb]
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.markdown("**3. Indicador Social**")
    dict_inds = {
        "SITS_INDEX": "🔥 Pobreza Extrema (Índice)",
        "CAR_POBREZA_20": "💰 Línea de Pobreza (Ingresos)",
        "CAR_ALIM_20": "🍲 Alimentación",
        "CAR_SERV_20": "🚰 Servicios Básicos",
        "CAR_VIV_20": "🏠 Calidad Vivienda",
        "CAR_SALUD_20": "🏥 Salud",
        "CAR_EDU_20": "🎓 Educación"
    }
    carencia_key = st.radio("Variable:", list(dict_inds.keys()), format_func=lambda x: dict_inds[x])
    st.markdown('</div>', unsafe_allow_html=True)

lbl_zona = sel_loc if sel_ageb == "TODAS" else f"{sel_loc} - AGEB {sel_ageb}"

# ==========================================
# 4. PESTAÑAS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ MAPA", "📊 ESTADÍSTICA", "⚖️ COMPARATIVA 2020-2025", "🚀 DECISIONES"])

# --- TAB 1: MAPA ---
with tab1:
    st.info(f"💡 **Explicación**: Visualización geoespacial de **{dict_inds[carencia_key]}**. Rojo indica alta marginación.")
    c1, c2 = st.columns([3, 1])
    with c1:
        if not du.empty:
            lat, lon = du.geometry.centroid.y.mean(), du.geometry.centroid.x.mean()
            zoom = 15 if sel_ageb != "TODAS" else 14
        elif not dr.empty:
            lat, lon = dr.geometry.centroid.y.mean(), dr.geometry.centroid.x.mean()
            zoom = 13
        else: lat, lon, zoom = 18.42, -95.11, 12

        m = folium.Map([lat, lon], zoom_start=zoom, tiles="CartoDB positron")
        
        def color(val): return '#800000' if val>=0.4 else '#ff0000' if val>=0.25 else '#ffa500' if val>=0.15 else '#ffff00' if val>0 else '#008000'

        if not du.empty:
            folium.Choropleth(geo_data=du, data=du, columns=['CVEGEO', carencia_key],
                key_on='feature.properties.CVEGEO', fill_color='YlOrRd', fill_opacity=0.7, line_opacity=0.1, name="Urbano").add_to(m)
            folium.GeoJson(du, tooltip=folium.GeoJsonTooltip(fields=['NOM_LOC','CVE_AGEB',carencia_key], aliases=['Loc','AGEB','Valor'])).add_to(m)

        if not dr.empty:
            for _, r in dr.iterrows():
                centro = r.geometry.centroid
                folium.CircleMarker([centro.y, centro.x], radius=6, color='#333', fill=True,
                                    fill_color=color(r[carencia_key]), fill_opacity=0.8,
                                    popup=f"{r['NOM_LOC']}: {r[carencia_key]:.1%}").add_to(m)
        st_folium(m, height=550)

    with c2:
        st.write(f"**Variable:** {dict_inds[carencia_key]}")
        st.write("🔴 Crítico (>40%)")
        st.write("🟠 Alto (25-40%)")
        st.write("🟡 Medio (15-25%)")
        st.write("🟢 Bajo (<15%)")

# --- TAB 2: ESTADÍSTICA (CORREGIDA) ---
with tab2:
    st.subheader(f"📊 Análisis Demográfico: {lbl_zona}")
    st.info("💡 **Explicación**: Analiza el impacto de la pobreza en grupos específicos (Mujeres, Indígenas, Discapacidad, etc.).")

    col_sel, col_kpi = st.columns([1, 3])
    with col_sel:
        st.markdown("**🎯 Filtro de Grupo:**")
        # LISTA COMPLETA RESTAURADA
        opciones_pob = {
            "Población Total": "P25_TOT",
            "Mujeres": "P25_FEM",
            "Hombres": "P25_MAS",
            "🏠 Hogares Jefatura Femenina": "P25_JEFAS",
            "💬 Lengua Indígena": "P25_IND",
            "🧡 Afromexicana": "P25_AFRO",
            "♿ Discapacidad": "P25_DISC",
            "Niños (0-14)": "P25_NINOS",
            "Adultos Mayores (60+)": "P25_MAYORES"
        }
        grupo_sel = st.selectbox("Seleccione Grupo:", list(opciones_pob.keys()))
        col_dato = opciones_pob[grupo_sel]

    df_zona = pd.concat([du, dr])
    
    if not df_zona.empty:
        # Blindaje
        if col_dato not in df_zona.columns: df_zona[col_dato] = 0
        
        tot = df_zona[col_dato].sum()
        afec = (df_zona[col_dato] * df_zona[carencia_key]).sum()
        intens = (afec / tot * 100) if tot > 0 else 0
        
        with col_kpi:
            k1, k2, k3 = st.columns(3)
            k1.markdown(f"""<div class="kpi-card"><div class="kpi-title">Total {grupo_sel} (2025)</div><div class="kpi-value">{int(tot):,}</div></div>""", unsafe_allow_html=True)
            k2.markdown(f"""<div class="kpi-card" style="border-left-color: #c0392b;"><div class="kpi-title">Afectados ({dict_inds[carencia_key]})</div><div class="kpi-value">{int(afec):,}</div></div>""", unsafe_allow_html=True)
            k3.markdown(f"""<div class="kpi-card" style="border-left-color: #f1c40f;"><div class="kpi-title">INTENSIDAD</div><div class="kpi-value">{intens:.1f}%</div></div>""", unsafe_allow_html=True)
            
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader(f"📉 Afectados por Tipo de Carencia ({grupo_sel})")
            st.info("Muestra cuántas personas de este grupo sufren cada carencia específica.")
            
            dims = ['CAR_POBREZA_20', 'CAR_ALIM_20', 'CAR_SERV_20', 'CAR_VIV_20', 'CAR_SALUD_20', 'CAR_EDU_20']
            noms = ['Pobreza $$', 'Alim', 'Serv', 'Viv', 'Salud', 'Edu']
            vals = [(df_zona[col_dato] * df_zona[d]).sum() for d in dims]
            
            fig_bar = px.bar(x=noms, y=vals, title="Volumen de Afectados", labels={'y':'Personas', 'x':''})
            fig_bar.update_traces(marker_color='#e74c3c')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with g2:
            st.subheader("📋 Padrón Focalizado")
            st.info("Lista de localidades/AGEBs ordenadas por urgencia para este grupo.")
            top = df_zona[['NOM_LOC', 'TIPO', 'CVE_AGEB', col_dato, carencia_key]].sort_values(carencia_key, ascending=False).head(15)
            st.dataframe(top.style.format({carencia_key: "{:.1%}", col_dato: "{:,.0f}"}), use_container_width=True)

# --- TAB 3: COMPARATIVA ---
with tab3:
    st.subheader("⚖️ Comparativa Real 2020 vs Proyección 2025")
    st.info("💡 **Explicación**: Compara los datos oficiales del Censo 2020 contra la proyección de crecimiento para 2025.")
    
    if not df_zona.empty:
        p20 = df_zona['P20_TOT'].sum()
        p25 = df_zona['P25_TOT'].sum()
        diff = p25 - p20
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Censo 2020", f"{int(p20):,}")
        c2.metric("Proyección 2025", f"{int(p25):,}")
        c3.metric("Crecimiento", f"{diff/p20*100:.1f}%", delta=f"+{int(diff)}")
        
        st.write("---")
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📈 Dinámica Poblacional")
            fig = go.Figure(data=[
                go.Bar(name='2020', x=['Población'], y=[p20], marker_color='#95a5a6'),
                go.Bar(name='2025', x=['Población'], y=[p25], marker_color='#2980b9')
            ])
            st.plotly_chart(fig, use_container_width=True)
            
        with g2:
            st.subheader("📉 Evolución de Índices (%)")
            dims = ['CAR_POBREZA_20', 'CAR_ALIM_20', 'CAR_SERV_20', 'CAR_VIV_20']
            noms = ['Pobreza', 'Alim', 'Serv', 'Viv']
            v20 = [df_zona[d].mean()*100 for d in dims]
            v25 = [x*0.95 for x in v20] 
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=noms, y=v20, name='2020', marker_color='#c0392b'))
            fig2.add_trace(go.Bar(x=noms, y=v25, name='2025', marker_color='#27ae60'))
            st.plotly_chart(fig2, use_container_width=True)

# --- TAB 4: DECISIONES ---
with tab4:
    st.subheader("🚀 Panel de Estrategia Integral")
    st.info("💡 **Explicación**: Listados prioritarios para asignación de presupuesto (Obras, Social) y análisis político-social.")
    
    t1, t2, t3 = st.tabs(["🏗️ OBRAS", "🚜 SOCIAL", "🗳️ ELECTORAL"])
    
    with t1:
        st.write("**Prioridad: Infraestructura (Agua/Drenaje/Luz)**")
        top = df_zona[['NOM_LOC', 'CVE_AGEB', 'CAR_SERV_20', 'P25_TOT']].sort_values('CAR_SERV_20', ascending=False).head(15)
        st.dataframe(top.style.format({'CAR_SERV_20': "{:.1%}"}), use_container_width=True)
        
    with t2:
        st.write("**Prioridad: Apoyos Directos (Línea de Pobreza)**")
        top = df_zona[['NOM_LOC', 'CVE_AGEB', 'CAR_POBREZA_20', 'P25_TOT']].sort_values('CAR_POBREZA_20', ascending=False).head(15)
        st.dataframe(top.style.format({'CAR_POBREZA_20': "{:.1%}"}), use_container_width=True)
        
    with t3:
        st.write("**Mapa Electoral Cruzado con Pobreza**")
        if gdf_p is not None:
            c1, c2 = st.columns([3, 1])
            with c1:
                mp = folium.Map([18.41, -95.11], zoom_start=11)
                folium.GeoJson(gdf_p, style_function=lambda x: {
                    'fillColor': {'morena':'#a50021','pan':'#005ba3','pri':'#00953b','mc':'#ff8300'}.get(str(x['properties']['GANADOR']).lower(), 'gray'),
                    'color':'black', 'weight':0.5, 'fillOpacity':0.6
                }, tooltip=folium.GeoJsonTooltip(fields=['SECCION', 'GANADOR'])).add_to(mp)
                st_folium(mp, height=400)
            
            with c2:
                pob_prom = df_zona['SITS_INDEX'].mean()
                st.metric("Pobreza en Zona Seleccionada", f"{pob_prom:.1%}")
                st.bar_chart(gdf_p['GANADOR'].value_counts())
