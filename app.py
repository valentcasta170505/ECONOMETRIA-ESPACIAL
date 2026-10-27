# -*- coding: utf-8 -*-
"""Spatial VAR Colombia — migración fiel del laboratorio Gradio/Colab a Streamlit.

Modelo original preservado: datos sintéticos, matrices Queen/KNN, A, RHO,
regla de propagación espacial, Moran y respuestas al impulso (h=0,…,8).
No se estiman parámetros a partir de datos DANE.
"""
import warnings
import html
import io
import json
from functools import lru_cache

import numpy as np
import pandas as pd
import geopandas as gpd
import requests
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from libpysal.weights import Queen, KNN
from esda.moran import Moran

st.set_page_config(page_title="Spatial VAR Colombia | Analytics Lab", page_icon="🌎",
                   layout="wide", initial_sidebar_state="expanded")

warnings.filterwarnings("ignore", message=".*is an island.*")
SEED = 20261020
RNG = np.random.default_rng(SEED)
PERIODOS = ["P1", "P2", "P3", "P4"]  # No atribuir fechas reales a datos inventados.
VARIABLES = {
    "Crecimiento económico (p.p.)": "growth",
    "Desempleo (p.p.)": "unemp",
    "Luces nocturnas (índice)": "nightlights",
}
LABELS = list(VARIABLES)
CODES = list(VARIABLES.values())
W_NAMES = ["Queen (contigüidad)", "KNN (4 vecinos)"]
PALETTES = ["Viridis", "Plasma", "Spectral", "Cividis", "Blues"]
C = {"ink": "#0f172a", "muted": "#475569", "blue": "#1d4ed8",
     "border": "#cbd5e1", "orange": "#c2410c", "teal": "#0f766e"}

# 1) GEOMETRÍAS (original + opción de subir un GeoJSON)
DANE_QUERY = (
    "https://geoportal.dane.gov.co/mparcgis/rest/services/Divipola/"
    "Serv_DIVIPOLA_MGN_2025/FeatureServer/319/query"
)
GITHUB_REAL = (
    "https://raw.githubusercontent.com/ytolosa/mapas-colombia/main/"
    "output/geojson/col_departamentos_real_nacional.geojson"
)
GEOBOUNDARIES_API = "https://www.geoboundaries.org/api/current/gbOpen/COL/ADM1/"


def _get_json(url, params=None, timeout=42):
    r = requests.get(url, params=params, timeout=timeout,
                     headers={"User-Agent": "Streamlit-SpatialVAR-Academic/1.0"})
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=24 * 3600, show_spinner="Cargando límites departamentales...")
def load_geometry(uploaded_bytes=None):
    errors = []
    attempts = [
        ("DANE · Marco Geoestadístico Nacional 2025 (oficial)", lambda: _get_json(
            DANE_QUERY,
            params={"where": "1=1", "outFields": "DPTO_CCDGO,DPTO_CNMBRE",
                    "returnGeometry": "true", "outSR": 4326,
                    "maxAllowableOffset": 0.01, "geometryPrecision": 4,
                    "f": "geojson"},
            timeout=55
        )),
        ("Repositorio público basado en MGN DANE (respaldo)",
         lambda: _get_json(GITHUB_REAL, timeout=35)),
        ("geoBoundaries · límites administrativos abiertos (respaldo)",
         lambda: _get_json(_get_json(GEOBOUNDARIES_API, timeout=25)["gjDownloadURL"],
                           timeout=40)),
    ]
    if uploaded_bytes is not None:
        # Única diferencia geográfica opcional respecto al código original.
        # Se carga el mapa que aporta el usuario si los servicios remotos fallan.
        if len(uploaded_bytes) > 25 * 1024 * 1024:
            raise ValueError("GeoJSON demasiado grande: máximo 25 MB.")
        custom_geo = json.loads(uploaded_bytes.decode("utf-8-sig"))
        attempts = [("GeoJSON proporcionado por usuario", lambda: custom_geo)]
    for source, getter in attempts:
        try:
            geo = getter()
            if not isinstance(geo, dict) or not geo.get("features"):
                raise ValueError("GeoJSON sin entidades geográficas")
            gdf = gpd.GeoDataFrame.from_features(geo["features"], crs="EPSG:4326")
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            else:
                gdf = gdf.to_crs("EPSG:4326")
            # Identificar denominación de los departamentos en distintas fuentes.
            aliases = ["dpto_cnmbre", "dpto_nombre", "departamento", "nom_dpto", "nombre_dpt",
                       "nombre", "shapeName", "name", "NAME_1", "adm1_name"]
            columns = {str(k).casefold(): k for k in gdf.columns}
            name_col = next((columns[x.casefold()] for x in aliases
                             if x.casefold() in columns), None)
            if name_col is None:
                raise ValueError(f"No se halló la columna de nombres: {list(gdf.columns)}")
            gdf = gdf.rename(columns={name_col: "departamento"})
            gdf["departamento"] = gdf["departamento"].astype(str).str.strip().str.title()
            gdf = gdf.loc[gdf.geometry.notna() & (~gdf.geometry.is_empty),
                          ["departamento", "geometry"]].copy()
            # Una entidad por departamento incluso si vino en partes separadas.
            if gdf["departamento"].duplicated().any():
                gdf = gdf.dissolve(by="departamento", as_index=False)
            gdf = gdf.sort_values("departamento").reset_index(drop=True)
            if not 30 <= len(gdf) <= 34:
                raise ValueError(f"Número inesperado de divisiones: {len(gdf)}")
            # Centroides calculados en proyección métrica (evita centrar en grados).
            cent = gdf.to_crs("EPSG:6933").centroid
            cent_ll = gpd.GeoSeries(cent, crs="EPSG:6933").to_crs("EPSG:4326")
            gdf["lon"] = cent_ll.x.to_numpy()
            gdf["lat"] = cent_ll.y.to_numpy()
            gdf["node_id"] = np.arange(len(gdf))
            return gdf, source
        except Exception as e:
            errors.append(f"- {source}: {type(e).__name__}: {str(e)[:170]}")
    raise RuntimeError(
        "No fue posible obtener geometrías reales. Comprueba el acceso a "
        "internet del servidor o carga un GeoJSON departamental.\n" + "\n".join(errors)
    )




st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f7f9fc; }
  .block-container { max-width: 1550px; padding-top: 1.7rem; }
  [data-testid="stSidebar"] { background: #f0f5ff; }
  .hero { background: linear-gradient(115deg,#e8f2ff,#fff 74%); border: 1px solid #bfd8ff;
      padding: 25px 30px; border-radius: 16px; margin-bottom: 19px; }
  .hero .eyebrow { color: #1e40af; letter-spacing: 2px; font-weight: 800;
      font-size: .77rem; text-transform: uppercase; }
  .hero h1 { color: #0f172a; font-weight: 850; font-size: clamp(27px,3vw,41px); margin: 7px 0; }
  .hero p { color: #334155; margin: 5px 0; }
  .kpi-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 13px; }
  .kpi { padding: 16px 18px; border:1px solid #cbd5e1; border-top:4px solid #1d4ed8;
      background: white; border-radius: 13px; }
  .kpi-label { color: #475569; font-size: .78rem; font-weight: 750; }
  .kpi-val { color: #0f172a; font-size: 1.68rem; font-weight: 850; padding-top: 5px; }
  .kpi-detail { color: #475569; font-size: .7rem; padding-top: 4px; }
  @media(max-width:950px){.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:540px){.kpi-grid{grid-template-columns:1fr} .hero{padding:18px}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🌎 Spatial VAR Lab")
    st.caption("Colombia · Herramienta académica")
    st.divider()
    uploaded_geo = st.file_uploader("GeoJSON alternativo (opcional)",
                                  type=["geojson", "json"],
                                  help="Archivo cartográfico de 30 a 34 divisiones administrativas departamentales.")
    st.caption("Sin archivo: primero consulta DANE, después repositorio público y geoBoundaries.")
    if st.button("🔄 Volver a descargar cartografía", use_container_width=True):
        load_geometry.clear()
        st.rerun()
    st.divider()
    st.info("Los mapas son reales; las variables económicas y coeficientes del modelo son simulados.")

try:
    GDF, GEO_SOURCE = load_geometry(uploaded_geo.getvalue() if uploaded_geo else None)
except Exception as exc:
    st.error("No fue posible preparar el mapa de Colombia. Intenta actualizar o cargar un GeoJSON válido desde el panel lateral.")
    with st.expander("Detalles técnicos"):
        st.code(str(exc))
    st.stop()


N = len(GDF)
COORDS = GDF[["lon", "lat"]].to_numpy(dtype=float)
DEPTS = GDF["departamento"].tolist()

# 2) PESOS ESPACIALES. Queen es pura: las islas conservan fila 0.
#    KNN emplea centroides métricos, NO grados de latitud/longitud.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    w_q = Queen.from_dataframe(GDF, use_index=False)
cent_metric = GDF.to_crs("EPSG:6933").centroid
xy_metros = np.column_stack([cent_metric.x, cent_metric.y])
w_knn = KNN.from_array(xy_metros, k=min(4, N - 1), ids=list(range(N)))
W_OBJ = {W_NAMES[0]: w_q, W_NAMES[1]: w_knn}
W_MAT = {}
for name, w in W_OBJ.items():
    w.transform = "r"  # suma de pesos por fila = 1, salvo islas Queen.
    W_MAT[name] = w.full()[0].astype(float)

# 3) SPATIAL VAR SIMULADO. NO es una estimación de parámetros empíricos.
#    Cada variable cumple: dy_j(t) = (I - rho_j W)^(-1) [A_j dy(t-1) + shock_j(t)]
#    A es la transmisión temporal y cruzada; rho es la difusión contemporánea.
A = np.array([[+0.52, -0.08, +0.06],
              [-0.28, +0.50, -0.025],
              [+0.22, -0.07, +0.47]], dtype=float)
RHO = np.array([0.26, 0.16, 0.19], dtype=float)
I_N = np.eye(N)

@lru_cache(maxsize=2)
def spatial_multipliers(weight_name):
    W = W_MAT[weight_name]
    return tuple(np.linalg.solve(I_N - float(rho) * W, I_N)
                 for rho in RHO)


def spatial_step(previous, disturbances, weight_name):
    """Un paso del modelo estructural de tres ecuaciones interconectadas."""
    rhs = previous @ A.T + disturbances
    out = np.empty_like(rhs)
    for j, mult in enumerate(spatial_multipliers(weight_name)):
        out[:, j] = mult @ rhs[:, j]
    return out


def synthetic_panel():
    """Datos ilustrativos con variabilidad regional y autocorrelación espacial."""
    multipliers = spatial_multipliers(W_NAMES[1])
    scales = np.array([0.55, 0.85, 5.2])
    region = RNG.normal(size=(N, 3)) * scales
    region = np.column_stack([multipliers[j] @ region[:, j]
                              for j in range(3)])
    state = region.copy()
    base = np.array([3.2, 11.2, 54.0])
    records = []
    for t, p in enumerate(PERIODOS):
        disturbance = RNG.normal(size=(N, 3)) * np.array([0.35, 0.55, 2.6])
        state = spatial_step(state, 0.30 * region + disturbance, W_NAMES[1])
        values = state + base
        values[:, 0] = np.clip(values[:, 0], -5.0, 12.0)
        values[:, 1] = np.clip(values[:, 1], 2.0, 26.0)
        values[:, 2] = np.clip(values[:, 2], 0.0, 100.0)
        for i in range(N):
            records.append({"departamento": DEPTS[i], "periodo": p,
                            "growth": float(values[i, 0]),
                            "unemp": float(values[i, 1]),
                            "nightlights": float(values[i, 2])})
    return pd.DataFrame(records)

PANEL = synthetic_panel()
PANEL_LOOKUP = {p: PANEL.loc[PANEL.periodo == p].set_index("departamento").loc[DEPTS]
                for p in PERIODOS}

# 4) VISUALIZACIÓN Y ESTADÍSTICOS

def pretty(v, digits=2):
    return f"{v:+,.{digits}f}" if v != 0 else f"{0:.{digits}f}"


def kpi_card(title, value, detail=""):
    return (f'<div class="kpi"><div class="kpi-label">{html.escape(str(title))}</div>'
            f'<div class="kpi-val">{html.escape(str(value))}</div>'
            f'<div class="kpi-detail">{html.escape(str(detail))}</div></div>')


def row_kpis(cards):
    return '<div class="kpi-grid">' + "".join(kpi_card(*card) for card in cards) + '</div>'


KPI_HTML = row_kpis([
    ("Unidades territoriales", str(N), "Geometrías reales de Colombia"),
    ("Panel ilustrativo", f"{len(PANEL)} filas", "4 períodos × departamentos"),
    ("Crecimiento medio P4", f"{PANEL_LOOKUP['P4'].growth.mean():.2f}%", "Dato simulado"),
    ("Desempleo medio P4", f"{PANEL_LOOKUP['P4'].unemp.mean():.2f}%", "Dato simulado"),
])


def configure_3d(fig, title, z_title, zrange=None):
    scene = dict(
        bgcolor="#ffffff",
        xaxis=dict(title="Longitud (°)", backgroundcolor="#ffffff",
                   gridcolor="#e2e8f0", color=C["ink"], showspikes=False),
        yaxis=dict(title="Latitud (°)", backgroundcolor="#ffffff",
                   gridcolor="#e2e8f0", color=C["ink"], showspikes=False),
        zaxis=dict(title=z_title, backgroundcolor="#ffffff",
                   gridcolor="#e2e8f0", color=C["ink"], showspikes=False),
        camera=dict(eye=dict(x=1.40, y=1.45, z=1.02)),
        aspectmode="manual", aspectratio=dict(x=1.25, y=1.0, z=0.70)
    )
    if zrange is not None:
        scene["zaxis"]["range"] = zrange
    fig.update_layout(
        template="plotly_white", title=dict(text=title, font=dict(size=17, color=C["ink"])),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color=C["ink"]),
        scene=scene, margin=dict(l=0, r=0, b=0, t=50), height=620,
        uirevision="spvar-3d"
    )
    return fig


def outline_lines(z0):
    """Dibuja contornos geográficos sobre el plano inferior del explorador."""
    xs, ys, zs = [], [], []
    # La simplificación es solo visual; Queen se calculó con geometrías completas.
    for geom in GDF.geometry.simplify(0.08, preserve_topology=True):
        polygons = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for polygon in polygons:
            if polygon.geom_type != "Polygon":
                continue
            for x, y in polygon.exterior.coords:
                xs.append(x); ys.append(y); zs.append(z0)
            xs.append(None); ys.append(None); zs.append(None)
    return xs, ys, zs


def explorer_plot(label, period, palette):
    code = VARIABLES[label]
    values = PANEL_LOOKUP[period][code].to_numpy()
    zfloor = float(min(values) - max(float(np.ptp(values)) * 0.2, 0.5))
    fig = go.Figure()
    xs, ys, zs = outline_lines(zfloor)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines",
                               line=dict(color="#94a3b8", width=2),
                               opacity=0.55, name="Límites geográficos", hoverinfo="skip"))
    stems_x, stems_y, stems_z = [], [], []
    for (x, y), z in zip(COORDS, values):
        stems_x.extend([x, x, None]); stems_y.extend([y, y, None])
        stems_z.extend([zfloor, float(z), None])
    fig.add_trace(go.Scatter3d(x=stems_x, y=stems_y, z=stems_z,
                               mode="lines", line=dict(color="#64748b", width=3),
                               opacity=0.55, name="Altura del indicador", hoverinfo="skip"))
    hover = [f"<b>{html.escape(dept)}</b><br>{html.escape(period)}<br>Valor: {v:.2f}"
             for dept, v in zip(DEPTS, values)]
    fig.add_trace(go.Scatter3d(
        x=COORDS[:, 0], y=COORDS[:, 1], z=values,
        mode="markers", name=label, hovertext=hover, hoverinfo="text",
        marker=dict(size=8.5, color=values, colorscale=palette,
                    line=dict(color=C["ink"], width=0.7), showscale=True,
                    colorbar=dict(title="Valor", len=0.68, thickness=14))
    ))
    configure_3d(fig, f"Territorio en 3D · {label} · {periodo_text(period)}", label)
    return fig


def periodo_text(period):
    return f"período simulado {period}"


def diagnostics(weight_name, period, variable_name):
    np.random.seed(SEED)  # Repetir p-valores Monte Carlo si no cambia la selección.
    w = W_OBJ[weight_name]
    W = W_MAT[weight_name]
    df = PANEL_LOOKUP[period]
    rows = []
    for label, code in VARIABLES.items():
        mor = Moran(df[code].to_numpy(), w, permutations=999, transformation="r")
        sign = "Positiva" if mor.I > 0 else "Negativa"
        rows.append({"Variable": label, "I de Moran": round(float(mor.I), 4),
                     "E[I]": round(float(mor.EI), 4),
                     "p Monte Carlo": round(float(mor.p_sim), 4),
                     "Autocorrelación": sign})
    v = df[VARIABLES[variable_name]].to_numpy(dtype=float)
    z = (v - v.mean()) / v.std(ddof=0)
    wz = W @ z
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=z, y=wz, mode="markers", name="Departamentos",
        text=DEPTS, hovertemplate="%{text}<br>z = %{x:.2f}<br>Wz = %{y:.2f}<extra></extra>",
        marker=dict(size=10, color=C["blue"], line=dict(color=C["ink"], width=0.7))
    ))
    slope = (z @ wz) / max(z @ z, 1e-10)
    xline = np.linspace(z.min() - 0.25, z.max() + 0.25, 100)
    fig.add_trace(go.Scatter(x=xline, y=slope * xline, mode="lines",
                             line=dict(color=C["orange"], width=3), name=f"Pendiente: {slope:.3f}"))
    fig.add_hline(y=0, line_color="#94a3b8", line_dash="dot")
    fig.add_vline(x=0, line_color="#94a3b8", line_dash="dot")
    fig.update_layout(template="plotly_white", height=420,
                      title=f"Diagrama de Moran · {variable_name} · {period}",
                      xaxis_title="Valor estandarizado (z)", yaxis_title="Rezago espacial (Wz)",
                      font=dict(color=C["ink"]), paper_bgcolor="white",
                      margin=dict(l=50, r=25, t=65, b=50))
    islands = len(w.islands)
    msg = (f"**Matriz:** {weight_name} · **N:** {N} · **Islas sin vecinos:** {islands}. "
           "Se emplean pesos normalizados por fila y 999 permutaciones. "
           "El p-valor Monte Carlo es una medida exploratoria; los indicadores son sintéticos. ")
    if islands:
        msg += ("**Queen conserva las islas desconectadas**; no se inventan "
                "fronteras ni vecinos para esos departamentos.")
    return pd.DataFrame(rows), fig, msg


# 5) LABORATORIO DE POLÍTICA: respuesta dinámica y descomposición espacial.
HORIZON = 8

def impulse_responses(weight_name, department_name, shock_pp):
    path = np.zeros((HORIZON + 1, N, 3), dtype=float)
    previous = np.zeros((N, 3), dtype=float)
    origin = DEPTS.index(department_name)
    for h in range(HORIZON + 1):
        innov = np.zeros((N, 3), dtype=float)
        if h == 0:
            innov[origin, 0] = float(shock_pp)  # Un solo impulso, no shock recurrente.
        previous = spatial_step(previous, innov, weight_name)
        path[h] = previous
    return path, origin


def impact_frame_traces(path, origin, w_name, target_idx, h, cmax):
    response = path[h, :, target_idx]
    W = W_MAT[w_name]
    # Cada flujo es una medida de sensibilidad del término rho_j * W_ij * y_j,
    # NO la atribución causal única de un borde (hay circuitos de retroalimentación).
    paths = []
    for recv in range(N):
        for source in np.flatnonzero(W[recv] > 0):
            if recv == source:
                continue
            flow = float(RHO[target_idx] * W[recv, source] * response[source])
            if abs(flow) > 1e-10:
                paths.append((abs(flow), flow, int(source), int(recv)))
    paths.sort(reverse=True)
    paths = paths[:max(30, min(75, len(paths)))]
    positive = [[], [], []]
    negative = [[], [], []]
    for _, flow, source, recv in paths:
        buf = positive if flow >= 0 else negative
        buf[0].extend([COORDS[source, 0], COORDS[recv, 0], None])
        buf[1].extend([COORDS[source, 1], COORDS[recv, 1], None])
        buf[2].extend([float(response[source]), float(response[recv]), None])
    edge_plus = go.Scatter3d(x=positive[0], y=positive[1], z=positive[2],
                             mode="lines", name="Canal espacial (+)",
                             line=dict(color="#d97706", width=5), opacity=0.60,
                             hoverinfo="skip")
    edge_minus = go.Scatter3d(x=negative[0], y=negative[1], z=negative[2],
                              mode="lines", name="Canal espacial (−)",
                              line=dict(color="#0891b2", width=5), opacity=0.60,
                              hoverinfo="skip")
    intensity = np.abs(response) / max(cmax, 1e-9)
    sizes = 5 + 11 * np.sqrt(intensity)
    nodes = go.Scatter3d(
        x=COORDS[:, 0], y=COORDS[:, 1], z=response,
        mode="markers", name="Respuesta regional",
        text=DEPTS,
        customdata=np.array([h] * N),
        hovertemplate="<b>%{text}</b><br>h = %{customdata}<br>Respuesta: %{z:+.4f}<extra></extra>",
        marker=dict(size=sizes, color=response, cmin=-cmax, cmax=cmax,
                    colorscale="RdBu_r", line=dict(color=C["ink"], width=0.7),
                    showscale=True, colorbar=dict(title="Δ respuesta", len=0.66, thickness=13))
    )
    focus = go.Scatter3d(
        x=[COORDS[origin, 0]], y=[COORDS[origin, 1]], z=[float(response[origin])],
        mode="markers", name="Departamento intervenido",
        text=[DEPTS[origin]],
        hovertemplate="Shock en <b>%{text}</b><br>Respuesta: %{z:+.4f}<extra></extra>",
        marker=dict(size=15, color="#f59e0b", symbol="diamond",
                    line=dict(color="#111827", width=2))
    )
    return [edge_plus, edge_minus, nodes, focus]


def policy_network_3d(path, origin, weight_name, target_name, initial_h):
    target_idx = CODES.index(VARIABLES[target_name])
    cmax = max(0.10, float(np.abs(path[:, :, target_idx]).max()))
    frames = [go.Frame(name=str(h),
                       data=impact_frame_traces(path, origin, weight_name,
                                                target_idx, h, cmax))
              for h in range(HORIZON + 1)]
    fig = go.Figure(data=impact_frame_traces(path, origin, weight_name,
                                             target_idx, initial_h, cmax),
                    frames=frames)
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="left", x=0.01, y=1.05,
                          showactive=False,
                          buttons=[dict(label="▶ Reproducir", method="animate",
                                        args=[None, dict(frame=dict(duration=850, redraw=True),
                                                         fromcurrent=True,
                                                         transition=dict(duration=100))]),
                                   dict(label="❚❚ Pausa", method="animate",
                                        args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                           mode="immediate")])])],
        sliders=[dict(active=int(initial_h), x=0.13, y=0.02, len=0.8,
                      currentvalue=dict(prefix="Horizonte: h = ",
                                        font=dict(size=13, color=C["ink"])),
                      steps=[dict(label=str(h), method="animate",
                                  args=[[str(h)], dict(mode="immediate",
                                                      frame=dict(duration=0, redraw=True),
                                                      transition=dict(duration=0))])
                             for h in range(HORIZON + 1)])]
    )
    configure_3d(fig, f"Grafo 3D de sensibilidad · {target_name}",
                 "Respuesta al impulso", [-1.18 * cmax, 1.18 * cmax])
    # El eje vertical conserva la misma escala durante toda la animación.
    fig.update_layout(margin=dict(l=0, r=0, b=32, t=78), height=660)
    return fig


def response_plot(path, origin):
    fig = make_subplots(rows=1, cols=3, subplot_titles=[
        "Crecimiento (p.p.)", "Desempleo (p.p.)", "Luces nocturnas (índice)"
    ], horizontal_spacing=0.075)
    h = list(range(HORIZON + 1))
    for j in range(3):
        local = path[:, origin, j]
        external_mean = (path[:, :, j].sum(axis=1) - local) / max(N - 1, 1)
        fig.add_trace(go.Scatter(x=h, y=local, mode="lines+markers",
                                 name="Departamento intervenido",
                                 legendgroup="local", showlegend=(j == 0),
                                 line=dict(color=C["blue"], width=3)), row=1, col=j + 1)
        fig.add_trace(go.Scatter(x=h, y=external_mean, mode="lines+markers",
                                 name="Promedio de otros departamentos",
                                 legendgroup="otros", showlegend=(j == 0),
                                 line=dict(color=C["orange"], width=2, dash="dot")),
                      row=1, col=j + 1)
        fig.update_xaxes(title_text="Horizonte h", dtick=1, row=1, col=j + 1)
        fig.add_hline(y=0, line_color="#cbd5e1", row=1, col=j + 1)
    fig.update_layout(template="plotly_white", height=395,
                      title="Respuesta impulso–respuesta de las tres ecuaciones",
                      font=dict(color=C["ink"]), legend=dict(orientation="h", y=-0.28),
                      paper_bgcolor="white", margin=dict(l=40, r=20, b=60, t=65))
    return fig


def policy_callback(department, shock, h, weight_name, target_name):
    h = int(h)
    path, origin = impulse_responses(weight_name, department, shock)
    # Descomposición exacta del impacto de crecimiento en el horizonte h=0.
    local = float(path[0, origin, 0])
    spill = float(path[0, :, 0].sum() - local)
    total = float(local + spill)
    target_idx = CODES.index(VARIABLES[target_name])
    current_total = float(path[h, :, target_idx].sum())
    kpis = row_kpis([
        ("Directo crecimiento · h=0", pretty(local), "Respuesta en el departamento origen"),
        ("Indirecto crecimiento · h=0", pretty(spill), "Suma de los demás departamentos"),
        ("Total crecimiento · h=0", pretty(total), "Directo + indirecto"),
        (f"Total territorial · h={h}", pretty(current_total), target_name),
    ])
    desc = (
        f"**Shock exógeno de {pretty(float(shock))} p.p. en {department}.** "
        f"Se utiliza **{weight_name}**. En el impacto inicial (h=0), "
        f"la respuesta directa del crecimiento es **{pretty(local)} p.p.**, "
        f"el efecto indirecto agregado es **{pretty(spill)} p.p.** y "
        f"la suma territorial es **{pretty(total)} puntos-departamento**. "
        "El efecto indirecto incorpora todas las rondas de difusión espacial "
        "contemporánea, no solo los vecinos inmediatos. "
        "**Precaución:** sumar puntos porcentuales regionales no produce una tasa "
        "nacional; faltan ponderadores económicos o poblacionales. "
        "Los coeficientes son supuestos didácticos, no estimaciones causales."
    )
    ranked = sorted([(DEPTS[i], float(path[h, i, target_idx])) for i in range(N)],
                    key=lambda pair: abs(pair[1]), reverse=True)
    table = pd.DataFrame([{"Departamento": name, "Respuesta": round(value, 5),
                           "Papel": "Origen del shock" if name == department else "Receptor"}
                          for name, value in ranked[:12]])
    return (kpis, policy_network_3d(path, origin, weight_name, target_name, h),
            response_plot(path, origin), table, desc)




# 6) INTERFAZ STREAMLIT — equivalente a las tres pestañas originales.
HEADER = f"""
<div class="hero">
  <div class="eyebrow">ECONOMETRÍA ESPACIAL · COLOMBIA</div>
  <h1>Spatial VAR · Territorial Analytics Lab</h1>
  <p>Exploración 3D, autocorrelación espacial y transmisión interregional de shocks.</p>
  <p><b>Geometría:</b> {html.escape(GEO_SOURCE)} ·
     <b>Indicadores económicos:</b> sintéticos, reproducibles y didácticos.</p>
</div>
"""

st.markdown(HEADER, unsafe_allow_html=True)
st.markdown(KPI_HTML, unsafe_allow_html=True)
st.warning("**Nota metodológica:** los departamentos sí utilizan geometrías reales de Colombia, "
           "pero el crecimiento, el desempleo y las luces nocturnas son simulados. "
           "El Policy Lab usa coeficientes supuestos: no son resultados de un modelo econométrico estimado ni efectos causales.")
st.caption(f"Cartografía cargada: {GEO_SOURCE} · {N} divisiones territoriales · {len(PANEL)} observaciones sintéticas")


def show_chart(figure, unique_key):
    st.plotly_chart(figure, use_container_width=True, key=unique_key,
                    config={"displaylogo": False, "responsive": True,
                            "toImageButtonOptions": {"format": "png", "scale": 2}})


def csv_button(frame, filename, title, unique_key):
    st.download_button(title, data=frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename, mime="text/csv", key=unique_key)


explorer_tab, diagnostic_tab, policy_tab = st.tabs([
    "01 · Explorador territorial 3D",
    "02 · Diagnósticos espaciales / ESDA",
    "03 · Policy Lab / Transmisión 3D",
])

with explorer_tab:
    st.subheader("Superficie de indicadores sobre el territorio")
    c1, c2, c3 = st.columns(3)
    with c1:
        exp_var = st.selectbox("Variable (eje Z)", LABELS, index=0)
    with c2:
        exp_period = st.selectbox("Período sintético", PERIODOS, index=3)
    with c3:
        exp_palette = st.selectbox("Paleta de colores", PALETTES, index=0)
    show_chart(explorer_plot(exp_var, exp_period, exp_palette), "explorer_3d")
    st.caption("Arrastra para rotar, usa la rueda para acercar y pasa el cursor por un "
               "departamento para leer su indicador simulado. La representación 3D es aproximada, no un SIG de precisión.")
    exp_data = PANEL_LOOKUP[exp_period].reset_index()[["departamento", VARIABLES[exp_var]]]
    st.dataframe(exp_data.rename(columns={"departamento": "Departamento", VARIABLES[exp_var]: exp_var}),
                 hide_index=True, use_container_width=True)
    csv_button(PANEL, "SpatialVAR_panel_SINTETICO.csv", "⬇️ Descargar panel simulado (CSV)", "download_panel")

with diagnostic_tab:
    st.subheader("Índice global de Moran · prueba por permutaciones")
    d1, d2, d3 = st.columns(3)
    with d1:
        esda_weight = st.selectbox("Matriz W", W_NAMES, index=1, key="esda_weight")
    with d2:
        esda_period = st.selectbox("Período", PERIODOS, index=3, key="esda_period")
    with d3:
        esda_variable = st.selectbox("Variable del diagrama", LABELS, index=0, key="esda_variable")
    esda_table, esda_figure, esda_summary = diagnostics(esda_weight, esda_period, esda_variable)
    st.dataframe(esda_table, hide_index=True, use_container_width=True)
    show_chart(esda_figure, "moran_plot")
    st.markdown(esda_summary)
    csv_button(esda_table, "SpatialVAR_Moran_SINTETICO.csv", "⬇️ Descargar diagnóstico Moran (CSV)", "download_moran")

with policy_tab:
    st.subheader("Simula un shock regional y observa su propagación espacial")
    p1, p2, p3 = st.columns([1.3, 1, 1.4])
    with p1:
        default_dept = DEPTS.index("Nariño") if "Nariño" in DEPTS else 0
        policy_dept = st.selectbox("Departamento de origen", DEPTS, index=default_dept)
    with p2:
        policy_shock = st.slider("Shock de crecimiento (p.p.)", -5.0, 5.0, 2.0, 0.25)
    with p3:
        policy_weight = st.selectbox("Red de transmisión", W_NAMES, index=1, key="policy_weight")
    p4, p5 = st.columns(2)
    with p4:
        policy_target = st.selectbox("Variable representada en el grafo", LABELS, index=0)
    with p5:
        policy_h = st.slider("Horizonte inicial (h)", 0, HORIZON, 2, 1)

    policy_cards, policy_graph, policy_curves, policy_table, policy_description = policy_callback(
        policy_dept, policy_shock, policy_h, policy_weight, policy_target
    )
    st.markdown(policy_cards, unsafe_allow_html=True)
    show_chart(policy_graph, "network_3d")
    st.caption("El color y altura de los nodos representan la respuesta simulada. Los enlaces de colores "
               "son términos espaciales ρ·W·Δy; no son flujos observados. "
               "Usa ▶ Reproducir y ❚❚ Pausa para recorrer los horizontes h=0…8.")
    show_chart(policy_curves, "impulse_response")
    st.markdown("#### 12 mayores respuestas territoriales (valor absoluto)")
    st.dataframe(policy_table, hide_index=True, use_container_width=True)
    st.markdown(policy_description)
    csv_button(policy_table, "SpatialVAR_respuestas_SINTETICAS.csv", "⬇️ Descargar respuestas (CSV)", "download_policy")

st.divider()
st.markdown("**Modelo conservado:** Δyⱼ,ₜ = (I − ρⱼW)⁻¹ [Σₖ AⱼₖΔyₖ,ₜ₋₁ + sⱼ,ₜ]. "
            "**Directo:** respuesta en el departamento intervenido. "
            "**Indirecto:** suma de respuestas en otros departamentos. "
            "**Total:** suma territorial; no equivale a una tasa nacional. "
            "**Cartografía:** [DANE MGN 2025](https://geoportal.dane.gov.co/), "
            "[repositorio de respaldo](https://github.com/ytolosa/mapas-colombia), "
            "[geoBoundaries](https://www.geoboundaries.org/). "
            "**Inferencia:** las pruebas de Moran se aplican a indicadores sintéticos.")
