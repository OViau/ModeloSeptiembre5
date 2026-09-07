"""
app.py
------
Dashboard en Streamlit para optimización de portafolio de proveedores
mediante el modelo de Frontera Eficiente de Markowitz.

Ejecutar localmente:
    streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from optimizer import (
    cargar_datos,
    filtrar_por_riesgo,
    calcular_estadisticos,
    optimizar_portafolio,
    calcular_frontera_eficiente,
)

DATA_PATH_DEFAULT = "data/BD_Gestion_Proveedores_Markowitz.xlsx"

AZUL = "#2E8BFF"
AZUL_CLARO = "#5FB4FF"
CIAN = "#00D4B5"
NEGRO = "#0B0F19"
GRIS_TARJETA = "#111827"
BLANCO = "#F5F7FA"
# Texto secundario: antes era un gris neutro (#9AA5B1) que se lavaba contra el
# fondo oscuro. Se reemplaza por un azul-grisáceo claro con más contraste,
# consistente con la paleta fintech (en vez de un gris "apagado" genérico).
GRIS_TEXTO = "#C3CEDE"

# ---------------------------------------------------------------------------
# Configuración de página y estilos
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Frontera Eficiente — Portafolio de Proveedores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            color: {BLANCO};
        }}

        .stApp {{
            background: radial-gradient(circle at top left, #101827 0%, {NEGRO} 55%);
        }}

        section[data-testid="stSidebar"] {{
            background-color: {GRIS_TARJETA};
            border-right: 1px solid rgba(255,255,255,0.06);
        }}

        h1, h2, h3, h4 {{
            color: {BLANCO} !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }}

        .hero {{
            padding: 1.6rem 2rem;
            border-radius: 18px;
            background: linear-gradient(120deg, rgba(46,139,255,0.16), rgba(0,212,181,0.08));
            border: 1px solid rgba(46,139,255,0.25);
            margin-bottom: 1.6rem;
        }}
        .hero h1 {{ margin: 0; font-size: 1.9rem; }}
        .hero p {{ color: {GRIS_TEXTO}; margin: 0.35rem 0 0 0; font-size: 0.95rem; }}
        .tag {{
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            background: rgba(46,139,255,0.18); color: {AZUL_CLARO};
            font-size: 0.72rem; font-weight: 600; letter-spacing: 0.04em;
            text-transform: uppercase; margin-bottom: 0.6rem;
        }}

        div[data-testid="stMetric"] {{
            background: {GRIS_TARJETA};
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 14px;
            padding: 1rem 1.2rem;
        }}
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * {{
            color: {GRIS_TEXTO} !important;
            -webkit-text-fill-color: {GRIS_TEXTO} !important;
            opacity: 1 !important;
        }}
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * {{
            color: {AZUL_CLARO} !important;
            -webkit-text-fill-color: {AZUL_CLARO} !important;
            opacity: 1 !important;
            font-weight: 700;
        }}

        .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
        .stTabs [data-testid="stTab"] {{
            background-color: {GRIS_TARJETA};
            border-radius: 10px 10px 0 0;
            padding: 0.5rem 1.1rem;
        }}
        .stTabs [data-testid="stTab"],
        .stTabs [data-testid="stTab"] * {{
            color: {GRIS_TEXTO} !important;
            -webkit-text-fill-color: {GRIS_TEXTO} !important;
            opacity: 1 !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: rgba(46,139,255,0.18) !important;
            border-bottom: 2px solid {AZUL} !important;
        }}
        .stTabs [aria-selected="true"],
        .stTabs [aria-selected="true"] * {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
            opacity: 1 !important;
        }}

        .stButton>button, .stDownloadButton>button {{
            background: linear-gradient(120deg, {AZUL}, {CIAN});
            color: {NEGRO};
            font-weight: 700;
            border: none;
            border-radius: 10px;
        }}

        /* --- Contraste de etiquetas de widgets (sidebar) --- */
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] label *,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] span {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] small,
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span {{
            color: {GRIS_TEXTO} !important;
            opacity: 1 !important;
        }}

        /* --- Uploader de archivos: versión oscura --- */
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
            background-color: {GRIS_TARJETA} !important;
            border: 1px dashed rgba(255,255,255,0.25) !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
            background-color: transparent !important;
            border: 1px solid {AZUL} !important;
            color: {AZUL_CLARO} !important;
        }}

        /* --- Acento azul para controles nativos (slider, radio, checkbox) ---
           Verificado en vivo: esta versión de Streamlit usa componentes
           react-aria sobre <input type="range"/"radio"> nativos, sin atributos
           data-baseweb. El color por defecto es "accent-color: auto", que seguía
           el color de acento del sistema operativo (por eso se veía rojo) en vez
           del tema de la app. Se fuerza explícitamente con accent-color. */
        input[type="range"],
        input[type="radio"],
        input[type="checkbox"] {{
            accent-color: {AZUL} !important;
        }}
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background-color: {GRIS_TARJETA} !important;
            border-color: rgba(255,255,255,0.15) !important;
            color: {BLANCO} !important;
        }}

        footer {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=BLANCO, size=13),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=BLANCO, size=12)),
    margin=dict(l=10, r=10, t=40, b=10),
)

EJE_COMUN = dict(
    tickfont=dict(color=GRIS_TEXTO, size=12),
    title_font=dict(color=BLANCO, size=13),
    gridcolor="rgba(255,255,255,0.10)",
    zerolinecolor="rgba(255,255,255,0.25)",
    linecolor="rgba(255,255,255,0.20)",
)


# ---------------------------------------------------------------------------
# Sidebar — Parámetros dinámicos
# ---------------------------------------------------------------------------
st.sidebar.markdown("## ⚙️ Parámetros del modelo")

archivo_usuario = st.sidebar.file_uploader(
    "Base de datos (.xlsx) — opcional, reemplaza la de ejemplo",
    type=["xlsx"],
)
fuente_datos = archivo_usuario if archivo_usuario is not None else DATA_PATH_DEFAULT

try:
    datos = cargar_datos(fuente_datos)
except Exception as e:
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

proveedores_raw = datos["proveedores"]
rendimientos = datos["rendimientos"]

st.sidebar.markdown("---")
st.sidebar.markdown("**Objetivo de optimización**")
objetivo_label = st.sidebar.radio(
    "Función objetivo",
    ["Máximo Sharpe", "Mínimo riesgo", "Máximo retorno"],
    label_visibility="collapsed",
)
objetivo_map = {
    "Máximo Sharpe": "sharpe",
    "Mínimo riesgo": "min_riesgo",
    "Máximo retorno": "max_retorno",
}
objetivo = objetivo_map[objetivo_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**Datos históricos**")
meses_disponibles = len(rendimientos)
ventana_meses = st.sidebar.select_slider(
    "Ventana histórica (meses)",
    options=sorted({v for v in [6, 12, 18, 24] if v <= meses_disponibles} | {meses_disponibles}),
    value=meses_disponibles,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Restricciones de portafolio**")
peso_max_pct = st.sidebar.slider("Peso máximo por proveedor (%)", 5, 100, 25, step=1)
peso_min_pct = st.sidebar.slider("Peso mínimo por proveedor activo (%)", 0, 10, 0, step=1)
peso_max = peso_max_pct / 100
peso_min = peso_min_pct / 100
rf_pct = st.sidebar.number_input("Tasa libre de riesgo anual, % (referencia CETES)", 0.0, 30.0, 8.0, step=0.5)
rf = rf_pct / 100

presupuesto_default = float(proveedores_raw["Volumen_Compra_Anual_MXN"].sum())
presupuesto_total = st.sidebar.number_input(
    "Presupuesto total a distribuir (MXN)",
    min_value=0.0,
    value=presupuesto_default,
    step=100000.0,
    format="%.0f",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filtros de riesgo cualitativo**")
max_r_ejec = st.sidebar.slider("Riesgo de ejecución máximo tolerado (%)", 0, 100, 100, step=5) / 100
max_r_com = st.sidebar.slider("Riesgo comercial máximo tolerado (%)", 0, 100, 100, step=5) / 100
max_r_fin = st.sidebar.slider("Riesgo financiero máximo tolerado (%)", 0, 100, 100, step=5) / 100

categorias_disponibles = sorted(proveedores_raw["Categoria"].unique())
categorias_sel = st.sidebar.multiselect(
    "Categorías incluidas", categorias_disponibles, default=categorias_disponibles
)

# ---------------------------------------------------------------------------
# Filtrado y cálculo de estadísticos
# ---------------------------------------------------------------------------
proveedores_filtrados = filtrar_por_riesgo(proveedores_raw, max_r_ejec, max_r_com, max_r_fin)
proveedores_filtrados = proveedores_filtrados[proveedores_filtrados["Categoria"].isin(categorias_sel)]

ids_validos = proveedores_filtrados["ID_Proveedor"].tolist()

if len(ids_validos) < 2:
    st.warning("Selecciona al menos 2 proveedores (ajusta los filtros de riesgo/categoría) para calcular el portafolio.")
    st.stop()

mu, cov = calcular_estadisticos(rendimientos, ids_validos, ventana_meses)

try:
    resultado = optimizar_portafolio(
        mu, cov, objetivo=objetivo, peso_min=peso_min, peso_max=peso_max, rf=rf
    )
except Exception as e:
    st.error(f"No fue posible optimizar el portafolio con los parámetros actuales: {e}")
    st.stop()

frontera = calcular_frontera_eficiente(mu, cov, peso_min=peso_min, peso_max=peso_max)

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
        <span class="tag">Markowitz · Portfolio Optimization</span>
        <h1>Frontera Eficiente — Portafolio de Proveedores</h1>
        <p>Optimización de la asignación de gasto entre proveedores tratando cada uno como un activo:
        utilidad esperada vs. riesgo de ejecución, comercial y financiero.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Retorno esperado (anual)", f"{resultado['retorno_esperado']:.1%}")
c2.metric("Riesgo (volatilidad anual)", f"{resultado['riesgo']:.1%}")
c3.metric("Sharpe Ratio", f"{resultado['sharpe']:.2f}")
c4.metric("Proveedores activos", f"{(resultado['pesos'] > 0).sum()} / {len(ids_validos)}")

st.write("")

# ---------------------------------------------------------------------------
# Tabs de contenido
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 Frontera eficiente", "🧩 Composición del portafolio", "🗂️ Datos y riesgo"])

# --- Tab 1: Frontera eficiente ------------------------------------------------
with tab1:
    rng = np.random.default_rng(7)
    n_sim = 3000
    n_activos = len(mu)
    pesos_sim = rng.dirichlet(np.ones(n_activos), size=n_sim)
    pesos_sim = np.clip(pesos_sim, 0, peso_max)
    pesos_sim = pesos_sim / pesos_sim.sum(axis=1, keepdims=True)

    ret_sim = pesos_sim @ mu.values
    riesgo_sim = np.sqrt(np.einsum("ij,jk,ik->i", pesos_sim, cov.values, pesos_sim))
    sharpe_sim = (ret_sim - rf) / riesgo_sim

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=riesgo_sim, y=ret_sim, mode="markers",
        marker=dict(
            size=5, color=sharpe_sim, colorscale="Blues", showscale=True,
            colorbar=dict(
                title=dict(text="Sharpe", font=dict(color=BLANCO, size=12)),
                tickfont=dict(color=GRIS_TEXTO, size=11),
                outlinewidth=0,
            ),
        ),
        name="Portafolios simulados", opacity=0.55,
        hovertemplate="Riesgo: %{x:.1%}<br>Retorno: %{y:.1%}<extra></extra>",
    ))

    if not frontera.empty:
        fig.add_trace(go.Scatter(
            x=frontera["riesgo"], y=frontera["retorno"], mode="lines",
            line=dict(color=CIAN, width=3), name="Frontera eficiente",
        ))

    fig.add_trace(go.Scatter(
        x=cov.values.diagonal() ** 0.5, y=mu.values, mode="markers+text",
        marker=dict(size=10, color=AZUL_CLARO, symbol="diamond", line=dict(width=1, color="white")),
        text=mu.index, textposition="top center", textfont=dict(size=11, color=BLANCO),
        name="Proveedores individuales",
        hovertemplate="%{text}<br>Riesgo: %{x:.1%}<br>Retorno: %{y:.1%}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=[resultado["riesgo"]], y=[resultado["retorno_esperado"]], mode="markers",
        marker=dict(size=16, color="#FFFFFF", symbol="star", line=dict(width=2, color=AZUL)),
        name=f"Portafolio óptimo ({objetivo_label})",
    ))

    fig.update_layout(
        **{**PLOTLY_LAYOUT, "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                                            font=dict(color=BLANCO, size=12), bgcolor="rgba(0,0,0,0)")},
        xaxis={**EJE_COMUN, "title": "Riesgo (volatilidad anual)", "tickformat": ".0%"},
        yaxis={**EJE_COMUN, "title": "Retorno esperado (anual)", "tickformat": ".0%"},
        height=560,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        f"<p style='color:{GRIS_TEXTO}; font-size:0.85rem;'>"
        "La nube de puntos son portafolios aleatorios (solo referencia visual). "
        "La línea es la frontera eficiente calculada; la estrella es el portafolio óptimo según el objetivo elegido."
        "</p>",
        unsafe_allow_html=True,
    )

# --- Tab 2: Composición -------------------------------------------------------
with tab2:
    pesos = resultado["pesos"].sort_values(ascending=False)
    pesos_activos = pesos[pesos > 0]

    tabla = proveedores_filtrados.set_index("ID_Proveedor").loc[pesos_activos.index, ["Nombre_Proveedor", "Categoria"]].copy()
    tabla["Peso_Asignado"] = pesos_activos.values
    tabla["Monto_Asignado_MXN"] = tabla["Peso_Asignado"] * presupuesto_total
    tabla = tabla.reset_index()

    col_izq, col_der = st.columns([1.1, 1])

    with col_izq:
        fig_bar = go.Figure(go.Bar(
            x=tabla["Peso_Asignado"], y=tabla["Nombre_Proveedor"], orientation="h",
            marker=dict(color=tabla["Peso_Asignado"], colorscale="Blues"),
            hovertemplate="%{y}<br>Peso: %{x:.1%}<extra></extra>",
        ))
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            xaxis={**EJE_COMUN, "tickformat": ".0%"},
            yaxis={**EJE_COMUN, "autorange": "reversed"},
            height=max(320, 34 * len(tabla)),
            title=dict(text="Distribución del gasto óptimo por proveedor", font=dict(color=BLANCO, size=15)),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_der:
        por_categoria = tabla.groupby("Categoria")["Peso_Asignado"].sum().sort_values(ascending=False)
        fig_pie = go.Figure(go.Pie(
            labels=por_categoria.index, values=por_categoria.values, hole=0.55,
            marker=dict(colors=["#2E8BFF", "#00D4B5", "#5FB4FF", "#7C4DFF", "#33C1FF", "#8FE3D0", "#4C6EF5", "#00A8CC"]),
            textfont=dict(color=NEGRO, size=12),
        ))
        fig_pie.update_layout(
            **{**PLOTLY_LAYOUT, "legend": dict(font=dict(color=BLANCO, size=12), bgcolor="rgba(0,0,0,0)")},
            title=dict(text="Concentración por categoría", font=dict(color=BLANCO, size=15)),
            height=380,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("#### Tabla de asignación óptima")
    st.dataframe(
        tabla.style.format({"Peso_Asignado": "{:.1%}", "Monto_Asignado_MXN": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

    csv = tabla.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar asignación (CSV)", csv, "portafolio_optimo_proveedores.csv", "text/csv")

# --- Tab 3: Datos y riesgo -----------------------------------------------------
with tab3:
    st.markdown("#### Matriz de correlación (rendimientos históricos)")
    corr = rendimientos[ids_validos].tail(ventana_meses).corr()
    fig_corr = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns,
        colorscale="RdBu", zmid=0,
        colorbar=dict(
            title=dict(text="ρ", font=dict(color=BLANCO, size=13)),
            tickfont=dict(color=GRIS_TEXTO, size=11),
            outlinewidth=0,
        ),
    ))
    fig_corr.update_layout(
        **PLOTLY_LAYOUT,
        xaxis={**EJE_COMUN, "tickfont": dict(color=GRIS_TEXTO, size=10)},
        yaxis={**EJE_COMUN, "tickfont": dict(color=GRIS_TEXTO, size=10)},
        height=520,
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("#### Universo de proveedores considerado")
    st.dataframe(
        proveedores_filtrados[[
            "ID_Proveedor", "Nombre_Proveedor", "Categoria",
            "Utilidad_Esperada_Anual_Pct", "Riesgo_Ejecucion_Pct",
            "Riesgo_Comercial_Pct", "Riesgo_Financiero_Pct",
            "Volumen_Compra_Anual_MXN",
        ]].style.format({
            "Utilidad_Esperada_Anual_Pct": "{:.1%}",
            "Riesgo_Ejecucion_Pct": "{:.1%}",
            "Riesgo_Comercial_Pct": "{:.1%}",
            "Riesgo_Financiero_Pct": "{:.1%}",
            "Volumen_Compra_Anual_MXN": "${:,.0f}",
        }),
        use_container_width=True, hide_index=True,
    )

st.markdown(
    f"<p style='color:{GRIS_TEXTO}; font-size:0.8rem; margin-top:2rem;'>"
    "Modelo con fines de análisis interno. Los datos de la base de ejemplo son sintéticos. "
    "El riesgo de mercado se estima con la covarianza histórica de rendimientos; los riesgos de "
    "ejecución, comercial y financiero se aplican como filtros de exclusión, no como parte de la "
    "matriz de covarianza."
    "</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Corrección de contraste inyectada al FINAL del script (a propósito).
#
# Streamlit pinta el texto de las etiquetas de widgets (stWidgetLabel) y de
# las métricas (stMetricLabel) dentro de un <span aria-hidden="true">, cuyo
# color se define en tiempo de ejecución (CSS-in-JS), no en una hoja de
# estilos estática. Ese estilo se inyecta en el <head> conforme cada
# componente se monta. Si nuestra hoja de estilos se inyecta antes que la de
# Streamlit, en un empate de especificidad + !important gana la de Streamlit
# por ir después en la cascada. Colocando este bloque al final del script,
# se inyecta después de todo lo demás y gana el orden de cascada.
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span * {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
            opacity: 1 !important;
        }}
        [data-testid="stMetricLabel"] span,
        [data-testid="stMetricLabel"] span * {{
            color: {GRIS_TEXTO} !important;
            -webkit-text-fill-color: {GRIS_TEXTO} !important;
            opacity: 1 !important;
        }}
        [data-testid="stMetricValue"] span,
        [data-testid="stMetricValue"] span * {{
            color: {AZUL_CLARO} !important;
            -webkit-text-fill-color: {AZUL_CLARO} !important;
            opacity: 1 !important;
        }}
        .stTabs [data-testid="stTab"] span,
        .stTabs [data-testid="stTab"] span * {{
            color: {GRIS_TEXTO} !important;
            -webkit-text-fill-color: {GRIS_TEXTO} !important;
            opacity: 1 !important;
        }}
        .stTabs [aria-selected="true"] span,
        .stTabs [aria-selected="true"] span * {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
            opacity: 1 !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)
