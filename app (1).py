"""Spatial VAR Lab Colombia — aplicación Streamlit lista para Community Cloud."""
from __future__ import annotations

import html
import json

import numpy as np
import pandas as pd
import streamlit as st

from engine import (
    A, HORIZON, PERIODS, RHO, VARIABLES, VARIABLE_NAMES, VARIABLE_CODES,
    WEIGHT_NAMES, fetch_remote_geojson, normalize_atlas, make_weights,
    synthetic_panel, panel_period, moran_table, global_moran,
    local_moran, irf, model_metadata,
)
from charts import (
    PALETTES, CLUSTER_COLORS, choropleth, explorer_3d, moran_scatter,
    lisa_map, network_3d, response_curves, weights_comparison, time_series,
)

st.set_page_config(page_title="Spatial VAR Lab | Colombia", page_icon="🌐",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  :root {color-scheme: light;}
  .stApp {background: #f6f8fc; color: #14233d;}
  [data-testid="stSidebar"] {background: #eef3fb; border-right: 1px solid #dbe3ef;}
  [data-testid="stMetric"] {background: white; border:1px solid #dbe3ef;
      border-top:4px solid #3562cf; padding:16px 17px; border-radius:15px;
      box-shadow:0 5px 20px rgba(17,37,64,.035);}
  [data-testid="stMetricValue"] {font-weight: 750;}
  .block-container {max-width:1530px; padding-top:1.3rem;}
  .hero {padding:24px 30px; background:linear-gradient(115deg,#11294c,#225ba4);
      border-radius:18px; color:white; margin-bottom:20px;
      box-shadow:0 8px 25px rgba(23,52,94,.11);}
  .hero .eyebrow {font-size:.75rem; letter-spacing:2px; opacity:.83; font-weight:750;}
  .hero h1 {font-size:2.25rem; line-height:1.2; letter-spacing:-.7px;
      color:white!important; margin:.5rem 0; font-weight:850;}
  .hero p {color:#eaf2ff!important; font-size:.97rem; margin:0;}
  .pill {display:inline-block; padding:5px 11px; margin-top:11px;
      font-size:.75rem; border-radius:100px; background:#def8ea; color:#115a3d;
      font-weight:750;}
  .info {border-left:4px solid #3562cf; background:#eaf0fb; padding:12px 16px;
      border-radius:7px; margin:10px 0 16px;}
  .smallnote {font-size:.85rem; color:#5b6c83;}
  h2, h3 {letter-spacing:-.3px;}
  @media(max-width:650px){.hero{padding:19px 17px}.hero h1{font-size:1.6rem}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=24 * 3600, show_spinner="Descargando cartografía departamental...")
def remote_cartography() -> tuple[str, str]:
    result, source = fetch_remote_geojson()
    return json.dumps(result, ensure_ascii=False), source


@st.cache_resource(show_spinner="Preparando geometrías y matrices espaciales...")
def initialize(raw_json: str, source: str):
    atlas = normalize_atlas(json.loads(raw_json), source)
    weights = make_weights(atlas)
    panel = synthetic_panel(atlas, weights)
    return atlas, weights, panel


def plot(fig, key: str | None = None):
    st.plotly_chart(fig, width="stretch", theme=None, key=key,
                    config={"displaylogo": False, "responsive": True,
                            "toImageButtonOptions": {"format": "png", "scale": 2}})


def download_csv(frame: pd.DataFrame, name: str, label: str):
    st.download_button(label, data=frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=name, mime="text/csv", use_container_width=True)


with st.sidebar:
    st.markdown("### 🌐 Spatial VAR Lab")
    st.caption("Simulación territorial • Colombia")
    st.divider()
    st.markdown("**Origen de la cartografía**")
    uploader = st.file_uploader("GeoJSON alternativo (opcional)", type=["geojson", "json"],
                               help="Archivo de 30–34 departamentos de Colombia con nombres de entidades.")
    if st.button("🔄 Actualizar cartografía", use_container_width=True):
        remote_cartography.clear()
        st.rerun()
    st.divider()
    weight_choice = st.selectbox("Matriz espacial principal", WEIGHT_NAMES, index=1,
                                 help="Queen requiere contacto real entre polígonos. "
                                      "KNN une los cuatro centroides más cercanos.")
    st.markdown("**Acerca de los datos**")
    st.caption("✅ Geometrías de fuentes públicas / archivo cargado")
    st.caption("⚠️ Indicadores y coeficientes simulados")
    st.caption("📚 Herramienta académica, no estimación causal")

try:
    if uploader is not None:
        raw = uploader.getvalue().decode("utf-8-sig")
        source = "GeoJSON proporcionado por el usuario (fuente no verificada)"
    else:
        raw, source = remote_cartography()
    atlas, weights, panel = initialize(raw, source)
except Exception as error:
    st.error("No se pudo iniciar el atlas. Comprueba el acceso a internet, "
             "actualiza la cartografía o adjunta un GeoJSON departamental válido.")
    with st.expander("Detalles para diagnóstico"):
        st.code(str(error))
    st.stop()

W = weights[weight_choice]
islands = [atlas.names[i] for i in np.flatnonzero(W.sum(axis=1) == 0)]

st.markdown("""
<div class="hero">
 <div class="eyebrow">ANÁLISIS ESPACIAL · ECONOMETRÍA APLICADA</div>
 <h1>Colombia · Spatial VAR Lab</h1>
 <p>Observatorio interactivo: exploración cartográfica, autocorrelación y transmisión territorial de shocks.</p>
 <span class="pill">Laboratorio didáctico · no son cifras oficiales</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
last = panel_period(panel, atlas.names, PERIODS[-1])
col1.metric("Unidades territoriales", f"{atlas.n}", help="Geometrías ADM1 cargadas")
col2.metric("Filas del panel sintético", f"{len(panel)}", help="Departamentos × 4 períodos")
col3.metric("Crecimiento medio · P4", f"{last.growth.mean():.2f} %",
            help="Promedio simple de cifras simuladas")
col4.metric("Desempleo medio · P4", f"{last.unemp.mean():.2f} %",
            help="Promedio simple de cifras simuladas")

st.caption(f"Cartografía: {source} · Matriz activa: {weight_choice} · "
           f"Departamentos sin vecinos bajo esta matriz: {len(islands)}")

section = st.radio("Navegación", ["🗺️ Explorador territorial", "📊 Moran y LISA",
                                    "⚡ Policy Lab 3D", "📘 Metodología y datos"],
                   horizontal=True, label_visibility="collapsed")
st.divider()

if section == "🗺️ Explorador territorial":
    st.subheader("Explorador territorial interactivo")
    one, two, three, four = st.columns([1.7, 1, 1, 1])
    with one:
        variable = st.selectbox("Indicador", VARIABLE_NAMES, key="explorer_variable")
    with two:
        period = st.select_slider("Período sintético", options=PERIODS, value="P4")
    with three:
        view = st.selectbox("Visualización", ("Mapa 2D", "Territorio 3D"))
    with four:
        palette = st.selectbox("Paleta", PALETTES)
    vals = panel_period(panel, atlas.names, period)[VARIABLES[variable]].to_numpy()
    chart_title = f"{variable} · período simulado {period}"
    if view == "Mapa 2D":
        plot(choropleth(atlas, vals, chart_title, palette), "mapa")
    else:
        plot(explorer_3d(atlas, vals, chart_title, palette), "territorio3d")
    st.caption("El color y, en 3D, la altura representan un indicador **simulado**. "
               "Los polígonos representan divisiones territoriales reales.")
    st.markdown("#### Distribución y evolución del indicador")
    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.dataframe(pd.DataFrame({"Departamento": atlas.names,
                                   "Valor simulado": np.round(vals, 3)}).sort_values(
                                       "Valor simulado", ascending=False),
                     use_container_width=True, hide_index=True, height=350)
    with c2:
        department = st.selectbox("Departamento para evolución", atlas.names,
                                  index=atlas.names.index("Nariño") if "Nariño" in atlas.names else 0)
        plot(time_series(panel, department, variable), "serie")
    download_csv(panel, "panel_territorial_SINTETICO.csv", "⬇️ Descargar panel completo (CSV)")

elif section == "📊 Moran y LISA":
    st.subheader("Autocorrelación espacial · diagnóstico ESDA")
    a, b, c = st.columns([1.25, 1, 1])
    with a:
        variable = st.selectbox("Indicador de análisis", VARIABLE_NAMES, key="moran_variable")
    with b:
        period = st.selectbox("Período", PERIODS, index=3, key="moran_period")
    with c:
        alpha = st.selectbox("Umbral exploratorio (α)", (.01, .05, .10), index=1)
    data = panel_period(panel, atlas.names, period)
    vals = data[VARIABLES[variable]].to_numpy()
    stats = global_moran(vals, W, seed=20261020 + PERIODS.index(period))
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Moran global (I)", f"{stats['I']:+.4f}")
    x2.metric("Valor esperado", f"{stats['E[I]']:+.4f}")
    x3.metric("p bilateral", f"{stats['p']:.4f}", help="999 permutaciones")
    x4.metric("Islas / sin vecinos", len(islands))
    left, right = st.columns(2)
    with left:
        plot(moran_scatter(vals, W, atlas.names, variable, period), "moran_scatter")
    with right:
        st.markdown("##### Comparación global de las tres variables")
        st.dataframe(moran_table(data, W, seed=20261020 + PERIODS.index(period)),
                     hide_index=True, use_container_width=True)
        st.info("Los valores p se obtienen por permutación bilateral sobre cifras sintéticas. "
                "Un resultado significativo no prueba causalidad.")
        if islands:
            st.warning("Queen mantiene desconectadas las islas: " + ", ".join(islands))
    st.markdown("#### Clústeres locales (LISA)")
    fdr = st.toggle("Aplicar corrección de Benjamini–Hochberg (FDR) a los p locales",
                    value=True)
    local = local_moran(vals, W, atlas.names, alpha=alpha, fdr=fdr,
                        seed=20261020 + PERIODS.index(period))
    left, right = st.columns([1.5, 1])
    with left:
        plot(lisa_map(atlas, local, "Patrones LISA · " + period), "lisa")
    with right:
        st.markdown("##### Clasificación local")
        summary = local["clúster"].value_counts()
        for label, color in CLUSTER_COLORS.items():
            if label in summary.index:
                st.markdown(f'<span style="color:{color};font-weight:900">●</span> '
                            f'{html.escape(label)}: **{int(summary[label])}**',
                            unsafe_allow_html=True)
        st.caption("LISA con 499 permutaciones condicionales por departamento. "
                   "Los patrones no significativos se muestran en gris. "
                   "La prueba es exploratoria.")
    st.dataframe(local[["departamento", "I local", "p local", "clúster"]],
                 hide_index=True, use_container_width=True)
    download_csv(local, "moran_local_SINTETICO.csv", "⬇️ Descargar resultados LISA (CSV)")

elif section == "⚡ Policy Lab 3D":
    st.subheader("Policy Lab · simulación de shocks espaciales")
    st.markdown("Define un shock único y observa la respuesta modelada de las tres variables "
                "en todos los departamentos durante nueve horizontes (h=0…8).")
    a, b, c = st.columns([1.2, 1.4, 1])
    with a:
        origin_name = st.selectbox("Departamento de origen", atlas.names,
                                   index=atlas.names.index("Nariño") if "Nariño" in atlas.names else 0)
    with b:
        shock_label = st.selectbox("Variable afectada por el shock", VARIABLE_NAMES)
    with c:
        shock = st.slider("Magnitud del impulso", -5.0, 5.0, 2.0, step=.25)
    a, b = st.columns([1.5, 1])
    with a:
        target_label = st.selectbox("Variable representada en el grafo", VARIABLE_NAMES)
    with b:
        initial_h = st.slider("Horizonte inicial", 0, HORIZON, 2)
    origin = atlas.names.index(origin_name)
    shock_idx = VARIABLE_CODES.index(VARIABLES[shock_label])
    target_idx = VARIABLE_CODES.index(VARIABLES[target_label])
    path = irf(W, origin, shock, variable=shock_idx)
    initial = path[0, :, shock_idx]
    local_direct = float(initial[origin])
    spill = float(initial.sum() - local_direct)
    target_total = float(path[initial_h, :, target_idx].sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Respuesta local inicial", f"{local_direct:+.3f}",
              help="En la variable que recibe el shock, h=0")
    m2.metric("Respuesta externa inicial", f"{spill:+.3f}",
              help="Suma no ponderada de otros departamentos, h=0")
    m3.metric("Suma territorial inicial", f"{initial.sum():+.3f}")
    m4.metric(f"Suma territorial · h={initial_h}", f"{target_total:+.3f}",
              help=f"Variable mostrada: {target_label}; suma no ponderada")
    st.caption("Las sumas territoriales son agregados aritméticos de respuestas "
               "departamentales, **no** estimaciones de tasas nacionales.")
    plot(network_3d(atlas, W, path, origin, target_idx, initial_h, target_label), "policy3d")
    st.caption("Arrastra para rotar, usa ▶ para animar los horizontes. "
               "Enlaces: sensibilidad del término espacial ρ·W·respuesta; "
               "no son flujos económicos observados ni rutas causales demostradas.")
    plot(response_curves(path, origin), "irfs")
    st.markdown("#### Respuestas territoriales y análisis de sensibilidad")
    c1, c2 = st.columns([1, 1])
    ranking = pd.DataFrame({
        "Departamento": atlas.names,
        "Respuesta": path[initial_h, :, target_idx],
        "Rol": ["Origen" if i == origin else "Receptor" for i in range(atlas.n)],
    }).sort_values("Respuesta", key=lambda s: s.abs(), ascending=False)
    with c1:
        st.markdown(f"**Departamentos con mayor respuesta absoluta (h={initial_h})**")
        st.dataframe(ranking.head(12).style.format({"Respuesta": "{:+.5f}"}),
                     hide_index=True, use_container_width=True, height=385)
    with c2:
        plot(weights_comparison(
            irf(weights[WEIGHT_NAMES[0]], origin, shock, shock_idx),
            irf(weights[WEIGHT_NAMES[1]], origin, shock, shock_idx),
            origin, target_idx), "sensitivity")
    download_csv(ranking, "respuestas_territoriales_SINTETICAS.csv",
                 "⬇️ Descargar respuestas de todos los departamentos")
    with st.expander("Interpretación de los efectos directo e indirecto"):
        st.markdown(
            f"Un shock didáctico de **{shock:+.2f}** unidades en **{shock_label}**, "
            f"originado en **{origin_name}**, genera en el momento inicial una "
            f"respuesta local de **{local_direct:+.4f}**, una suma de "
            f"respuestas externas de **{spill:+.4f}** y una suma territorial de "
            f"**{initial.sum():+.4f}**. El modelo permite retroalimentación espacial "
            "contemporánea; por eso la respuesta local puede superar la magnitud "
            "del shock. Las trayectorias no son pronósticos ni impactos causales estimados."
        )

else:
    st.subheader("Metodología, datos y reproducibilidad")
    st.markdown("##### 1. Diferencia entre cartografía y datos económicos")
    st.markdown("La forma de los departamentos proviene de una fuente cartográfica "
                "pública o del GeoJSON cargado. **Crecimiento, desempleo y luces nocturnas "
                "son valores generados por computadora**, no mediciones DANE, "
                "DNP ni de satélites. P1–P4 no representan años reales.")
    st.markdown("##### 2. Tres ecuaciones dinámicas interconectadas")
    st.latex(r"\Delta\mathbf y_t^{(j)}=(I-\rho_j W)^{-1}"
             r"\left(\sum_{k=1}^{3} A_{jk}\Delta\mathbf y_{t-1}^{(k)}"
             r"+\mathbf s_t^{(j)}\right),\quad j=1,2,3")
    st.markdown("La matriz **A** transmite respuestas temporales y cruzadas entre "
                "las tres variables. Cada parámetro **ρⱼ** genera difusión espacial "
                "contemporánea mediante la matriz **W**. Estos coeficientes son "
                "supuestos fijados para enseñar, no resultados econométricos estimados.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Matriz de transmisión temporal A**")
        st.dataframe(pd.DataFrame(A, index=VARIABLE_CODES, columns=VARIABLE_CODES).round(3),
                     use_container_width=True)
    with c2:
        st.markdown("**Coeficientes de difusión espacial ρ**")
        st.dataframe(pd.DataFrame({"Variable": VARIABLE_NAMES, "ρ": RHO}),
                     hide_index=True, use_container_width=True)
    st.markdown("##### 3. Matrices espaciales y pruebas")
    st.markdown("**Queen:** contigüidad por frontera o vértice de polígonos; las "
                "unidades insulares pueden quedar aisladas. **KNN-4:** cuatro vecinos "
                "por proximidad de centroides en coordenadas métricas (EPSG:6933). "
                "Se normalizan las filas (las islas mantienen ceros). Los p-valores "
                "globales de Moran usan 999 permutaciones bilaterales. LISA usa 499 "
                "permutaciones condicionales; puede añadirse una corrección FDR. "
                "Son diagnósticos exploratorios.")
    st.markdown("##### 4. Restricciones del experimento")
    st.warning("**Este laboratorio no estima un Spatial VAR a partir de datos reales.** "
               "Un panel de cuatro períodos sintéticos no permite presentar resultados "
               "como evidencia de causalidad, impactos reales o cifras nacionales.")
    st.markdown("##### 5. Fuentes geográficas y datos disponibles")
    st.markdown("- [Geoportal DANE](https://geoportal.dane.gov.co/) "
                "(consulta MGN, cuando está disponible).\n"
                "- [Repositorio público de cartografía colombiana]"
                "(https://github.com/ytolosa/mapas-colombia) (respaldo).\n"
                "- [geoBoundaries](https://www.geoboundaries.org/) (respaldo ADM1, "
                "licencia según la fuente).")
    st.caption("Fuente cargada en esta sesión: " + source)
    c1, c2 = st.columns(2)
    with c1:
        download_csv(panel, "panel_territorial_SINTETICO.csv", "⬇️ Panel sintético (CSV)")
    with c2:
        st.download_button("⬇️ Ficha metodológica (JSON)",
                           data=json.dumps(model_metadata(atlas), indent=2,
                                           ensure_ascii=False).encode("utf-8"),
                           file_name="metadatos_spvar.json", mime="application/json",
                           use_container_width=True)

st.divider()
st.caption("Spatial VAR Lab Colombia · Demostración académica reproducible · "
           "Geometrías geográficas reales; modelo e indicadores económicos simulados.")
