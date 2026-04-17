"""
DASHBOARD FCIs - Argentina (v2)
================================
Correr con: python dashboard_fci.py
Requiere:   pip install dash dash-bootstrap-components dash-ag-grid plotly requests pandas

Luego abrí: http://localhost:8050

Tabs:
  1. Resumen       - KPIs globales y distribución de renta fija
  2. Por Tipo      - análisis comparado de renta fija/variable/MM/mixta
  3. Administradoras - ranking de managers del mercado argentino
  4. Comparador    - compara evolución de VCP entre fondos
  5. Scorecard     - tabla de fondos con RiskScore (estilo Tech Risk)
"""

import sys
from pathlib import Path

# Permite importar desde la carpeta padre (data_layer / analisis)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, date

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

from data_layer import DataLayer, TIPOS_ENDPOINT
from analisis import (
    rendimiento_anual, rendimiento_todos_tipos, agregar_rendimiento_real,
    ranking_administradoras, risk_scorecard, serie_comparativa,
)

# ══════════════════════════════════════════════
# PALETA Y ESTILOS
# ══════════════════════════════════════════════
VERDE    = "#00C48C"
ROJO     = "#FF5C6A"
AMARILLO = "#FFB547"
AZUL     = "#4C8BF5"
MAGENTA  = "#B366FF"
BG       = "#0F1117"
CARD_BG  = "#1A1D27"
BORDE    = "#2A2D3E"
TEXTO    = "#E8EAF0"
TEXTO2   = "#8B8FA8"

CARD_STYLE = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {BORDE}",
    "borderRadius": "12px",
    "padding": "20px",
}

COLORES_TIPO = {
    "Renta Fija":     AZUL,
    "Renta Variable": MAGENTA,
    "Mercado Dinero": VERDE,
    "Renta Mixta":    AMARILLO,
}


def layout_plotly(fig, title=""):
    fig.update_layout(
        title=title,
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font_color=TEXTO, font_family="Inter, sans-serif",
        xaxis=dict(gridcolor=BORDE, color=TEXTO2),
        yaxis=dict(gridcolor=BORDE, color=TEXTO2),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ══════════════════════════════════════════════
# CARGA INICIAL
# ══════════════════════════════════════════════
print("⏳ Inicializando DataLayer...")
dl = DataLayer()

print("⏳ Bajando snapshot + calculando rendimientos de todos los tipos...")
df_snapshot    = dl.snapshot_diario()          # todos los tipos, hoy
inflacion_12m  = dl.inflacion_acumulada(12)
df_rend_all    = rendimiento_todos_tipos(dl, 365)
df_rend_all    = agregar_rendimiento_real(df_rend_all, inflacion_12m)
df_rend_fija   = df_rend_all[df_rend_all["tipo"] == "Renta Fija"].copy()
df_ranking     = ranking_administradoras(df_rend_all, inflacion_12m)
df_scorecard   = risk_scorecard(df_rend_all, df_snapshot, inflacion_12m)

print(f"✅ {len(df_snapshot)} fondos snapshot | {len(df_rend_all)} con rendimiento | "
      f"{len(df_ranking)} admins | inflación 12m {inflacion_12m}%")


# ══════════════════════════════════════════════
# COMPONENTES REUSABLES
# ══════════════════════════════════════════════
def kpi_card(titulo, valor, subtitulo, color=TEXTO, tooltip=None):
    return dbc.Col(
        html.Div([
            html.P(titulo, style={"color": TEXTO2, "fontSize": "12px",
                                  "marginBottom": "4px", "textTransform": "uppercase",
                                  "letterSpacing": "1px"}),
            html.H3(valor, style={"color": color, "fontWeight": "700", "margin": "0"}),
            html.P(subtitulo, style={"color": TEXTO2, "fontSize": "12px",
                                     "marginTop": "4px"}),
        ], style=CARD_STYLE, title=tooltip or ""),
        md=3, sm=6, xs=12
    )


# ══════════════════════════════════════════════
# TAB 1 — RESUMEN
# ══════════════════════════════════════════════
def build_histograma(df, inflacion):
    if df is None or df.empty:
        return layout_plotly(go.Figure(), "Sin datos")
    colores = [VERDE if r > inflacion else ROJO for r in df["rendimiento_%"]]
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["rendimiento_%"], nbinsx=40, marker_color=colores, opacity=0.85,
    ))
    fig.add_vline(x=inflacion, line_dash="dash", line_color=AMARILLO,
                  annotation_text=f"Inflación {inflacion}%",
                  annotation_font_color=AMARILLO, annotation_position="top right")
    fig.add_vline(x=df["rendimiento_%"].median(), line_dash="dot", line_color=AZUL,
                  annotation_text=f"Mediana {df['rendimiento_%'].median():.1f}%",
                  annotation_font_color=AZUL, annotation_position="top left")
    return layout_plotly(fig, "Distribución de rendimientos — Renta Fija (último año)")


def build_torta(gana, pierde, pct):
    fig = go.Figure(go.Pie(
        labels=[f"Ganaron ({gana})", f"No ganaron ({pierde})"],
        values=[gana, pierde],
        marker_colors=[VERDE, ROJO],
        hole=0.55, textinfo="percent", textfont_size=13,
    ))
    fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font_color=TEXTO, showlegend=True,
        legend=dict(orientation="h", x=0, y=-0.15, font_color=TEXTO2),
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[dict(text=f"{pct}%", x=0.5, y=0.5,
                           font_size=28, font_color=VERDE, showarrow=False)]
    )
    return fig


def tab_resumen_layout():
    ganadores  = int((df_rend_fija["rendimiento_%"] > inflacion_12m).sum())
    perdedores = len(df_rend_fija) - ganadores
    total      = len(df_rend_fija)
    pct_gana   = round(ganadores / total * 100) if total else 0
    mediana    = round(df_rend_fija["rendimiento_%"].median(), 1) if total else 0

    kpis = dbc.Row([
        kpi_card("Fondos analizados", f"{total:,}", "Renta fija (sin outliers)"),
        kpi_card("Le ganaron inflación", f"{pct_gana}%",
                 f"{ganadores} de {total}", VERDE),
        kpi_card("Rendimiento mediano", f"{mediana}%", "Último año",
                 VERDE if mediana > inflacion_12m else ROJO),
        kpi_card("Inflación 12m", f"{inflacion_12m}%", "Benchmark real"),
    ], className="g-3 mb-4")

    filtros = html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Horizonte", style={"color": TEXTO2, "fontSize": "12px",
                                                "textTransform": "uppercase"}),
                dcc.Dropdown(
                    id="filtro-horizonte",
                    options=[{"label": h.capitalize(), "value": h}
                             for h in sorted(df_rend_fija["horizonte"].dropna().unique())],
                    placeholder="Todos", multi=True,
                    style={"backgroundColor": CARD_BG},
                ),
            ], md=4),
            dbc.Col([
                html.Label("Rendimiento mínimo (%)", style={"color": TEXTO2,
                                                            "fontSize": "12px",
                                                            "textTransform": "uppercase"}),
                dcc.Slider(
                    id="filtro-rendimiento",
                    min=-50, max=200, step=5, value=-50,
                    marks={-50: "-50%", 0: "0%",
                           int(inflacion_12m): f"Inf {inflacion_12m}%",
                           100: "100%", 200: "200%"},
                    tooltip={"placement": "bottom"},
                    className="slider-texto",
                ),
            ], md=8),
        ], className="g-3"),
    ], style={**CARD_STYLE, "marginBottom": "24px"})

    graficos = dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="grafico-histograma",
                                    figure=build_histograma(df_rend_fija, inflacion_12m),
                                    config={"displayModeBar": False}), style=CARD_STYLE), md=8),
        dbc.Col(html.Div([
            html.P("¿Le ganaron a la inflación?", style={"color": TEXTO2,
                                                          "fontSize": "12px",
                                                          "textTransform": "uppercase",
                                                          "marginBottom": "0"}),
            dcc.Graph(id="grafico-torta",
                      figure=build_torta(ganadores, perdedores, pct_gana),
                      config={"displayModeBar": False}),
        ], style=CARD_STYLE), md=4),
    ], className="mb-4 g-3")

    tabla = html.Div([
        html.P("Detalle por fondo — Renta Fija", style={"color": TEXTO2,
                                                         "fontSize": "12px",
                                                         "textTransform": "uppercase",
                                                         "marginBottom": "12px"}),
        html.Div(id="contenedor-tabla", children=build_grid_resumen(df_rend_fija)),
    ], style=CARD_STYLE)

    return html.Div([kpis, filtros, graficos, tabla])


def build_grid_resumen(df):
    if df is None or df.empty:
        return dag.AgGrid(rowData=[], columnDefs=[])
    df_grid = df.copy()
    df_grid["ganó_inflación"] = df_grid["rendimiento_%"].apply(
        lambda x: "✅ Sí" if x > inflacion_12m else "❌ No")
    df_grid["patrimonio_M"] = (df_grid["patrimonio"] / 1e6).round(1).fillna(0)

    col_defs = [
        {"field": "fondo", "headerName": "Fondo", "minWidth": 280, "filter": True, "sortable": True},
        {"field": "administradora", "headerName": "Administradora", "width": 160, "filter": True},
        {"field": "horizonte", "headerName": "Horizonte", "width": 110, "filter": True},
        {"field": "rendimiento_%", "headerName": "Rend %", "width": 110, "sortable": True,
         "cellStyle": {"function": f"params.value > {inflacion_12m} ? "
                                    f"{{'color': '{VERDE}', 'fontWeight': '600'}} : "
                                    f"{{'color': '{ROJO}', 'fontWeight': '600'}}"}},
        {"field": "rendimiento_real_%", "headerName": "Rend Real %", "width": 125, "sortable": True,
         "cellStyle": {"function": f"params.value > 0 ? "
                                    f"{{'color': '{VERDE}', 'fontWeight': '600'}} : "
                                    f"{{'color': '{ROJO}', 'fontWeight': '600'}}"}},
        {"field": "ganó_inflación", "headerName": "¿Ganó inf?", "width": 120},
        {"field": "patrimonio_M", "headerName": "Patrimonio (M$)", "width": 150, "sortable": True},
    ]
    return dag.AgGrid(
        id="tabla-fondos",
        rowData=df_grid.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={"resizable": True, "sortable": True},
        dashGridOptions={"pagination": True, "paginationPageSize": 15, "animateRows": True},
        style={"height": "500px"},
        className="ag-theme-alpine-dark",
    )


# ══════════════════════════════════════════════
# TAB 2 — POR TIPO
# ══════════════════════════════════════════════
def build_box_por_tipo(df, inflacion):
    fig = go.Figure()
    for tipo, color in COLORES_TIPO.items():
        sub = df[df["tipo"] == tipo]
        if sub.empty:
            continue
        fig.add_trace(go.Box(
            y=sub["rendimiento_%"], name=tipo, marker_color=color,
            boxpoints="outliers", line_width=1.5,
        ))
    fig.add_hline(y=inflacion, line_dash="dash", line_color=AMARILLO,
                  annotation_text=f"Inflación {inflacion}%",
                  annotation_font_color=AMARILLO)
    return layout_plotly(fig, "Dispersión de rendimientos por tipo de fondo")


def build_bar_ganadores(df, inflacion):
    agg = df.groupby("tipo").apply(
        lambda g: pd.Series({
            "total": len(g),
            "ganaron": int((g["rendimiento_%"] > inflacion).sum()),
        })
    ).reset_index()
    agg["pct_ganaron"] = (agg["ganaron"] / agg["total"] * 100).round(0)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg["tipo"], y=agg["pct_ganaron"],
        marker_color=[COLORES_TIPO.get(t, AZUL) for t in agg["tipo"]],
        text=[f"{p}%<br>({g}/{t})" for p, g, t in zip(agg["pct_ganaron"],
                                                        agg["ganaron"],
                                                        agg["total"])],
        textposition="outside",
    ))
    fig.update_yaxes(range=[0, max(100, agg["pct_ganaron"].max() + 20)])
    return layout_plotly(fig, "% de fondos que le ganaron a la inflación — por tipo")


def tab_portipo_layout():
    kpis = []
    for tipo, color in COLORES_TIPO.items():
        sub = df_rend_all[df_rend_all["tipo"] == tipo]
        if sub.empty:
            continue
        mediana = round(sub["rendimiento_%"].median(), 1)
        kpis.append(kpi_card(
            f"{tipo}", f"{mediana}%",
            f"{len(sub)} fondos · mediana anual",
            color=color,
        ))
    kpi_row = dbc.Row(kpis, className="g-3 mb-4")

    graficos = dbc.Row([
        dbc.Col(html.Div(dcc.Graph(
            figure=build_box_por_tipo(df_rend_all, inflacion_12m),
            config={"displayModeBar": False}), style=CARD_STYLE), md=7),
        dbc.Col(html.Div(dcc.Graph(
            figure=build_bar_ganadores(df_rend_all, inflacion_12m),
            config={"displayModeBar": False}), style=CARD_STYLE), md=5),
    ], className="mb-4 g-3")

    # Top 5 por tipo
    cards_top = []
    for tipo in COLORES_TIPO.keys():
        sub = df_rend_all[df_rend_all["tipo"] == tipo].head(5)[
            ["fondo", "rendimiento_%", "rendimiento_real_%"]
        ]
        if sub.empty:
            continue
        rows = [html.Tr([
            html.Td(r["fondo"], style={"fontSize": "11px", "maxWidth": "250px",
                                        "overflow": "hidden",
                                        "textOverflow": "ellipsis"}),
            html.Td(f"{r['rendimiento_%']}%",
                    style={"color": VERDE, "textAlign": "right",
                           "fontSize": "12px"}),
            html.Td(f"{r['rendimiento_real_%']}%",
                    style={"color": VERDE if r["rendimiento_real_%"] > 0 else ROJO,
                           "textAlign": "right", "fontSize": "12px"}),
        ]) for _, r in sub.iterrows()]
        cards_top.append(dbc.Col(html.Div([
            html.P(f"Top 5 · {tipo}",
                   style={"color": COLORES_TIPO[tipo], "fontSize": "13px",
                          "textTransform": "uppercase", "fontWeight": "600",
                          "marginBottom": "8px"}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Fondo", style={"fontSize": "11px", "color": TEXTO2}),
                    html.Th("Nominal", style={"fontSize": "11px", "color": TEXTO2,
                                               "textAlign": "right"}),
                    html.Th("Real", style={"fontSize": "11px", "color": TEXTO2,
                                            "textAlign": "right"}),
                ])),
                html.Tbody(rows),
            ], style={"width": "100%", "color": TEXTO}),
        ], style=CARD_STYLE), md=6))
    top_row = dbc.Row(cards_top, className="g-3")

    return html.Div([kpi_row, graficos, top_row])


# ══════════════════════════════════════════════
# TAB 3 — ADMINISTRADORAS
# ══════════════════════════════════════════════
def build_bar_admins(df):
    top = df.head(20)
    colores = [VERDE if r > inflacion_12m else ROJO for r in top["rend_mediano"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top["administradora"][::-1], x=top["rend_mediano"][::-1],
        orientation="h", marker_color=colores[::-1],
        text=[f"{r}% ({n})" for r, n in zip(top["rend_mediano"][::-1],
                                              top["n_fondos"][::-1])],
        textposition="outside",
    ))
    fig.add_vline(x=inflacion_12m, line_dash="dash", line_color=AMARILLO,
                  annotation_text=f"Inflación {inflacion_12m}%",
                  annotation_font_color=AMARILLO)
    fig.update_layout(height=600)
    return layout_plotly(fig, "Rendimiento mediano por administradora (top 20)")


def build_scatter_admins(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["n_fondos"], y=df["rend_mediano"],
        mode="markers+text",
        marker=dict(
            size=df["patrimonio_MM$"].clip(1, 50) * 2 + 8,
            color=df["pct_ganaron"],
            colorscale=[[0, ROJO], [0.5, AMARILLO], [1, VERDE]],
            colorbar=dict(title="% ganaron<br>inflación", title_font_color=TEXTO2),
            line=dict(color=BORDE, width=1),
        ),
        text=df["administradora"],
        textposition="top center",
        textfont=dict(size=10, color=TEXTO2),
        hovertemplate="<b>%{text}</b><br>Fondos: %{x}<br>Rend mediano: %{y}%<extra></extra>",
    ))
    fig.add_hline(y=inflacion_12m, line_dash="dash", line_color=AMARILLO)
    return layout_plotly(fig, "Administradoras: tamaño vs performance")


def build_grid_admins(df):
    col_defs = [
        {"field": "administradora", "headerName": "Administradora", "minWidth": 220,
         "filter": True, "sortable": True},
        {"field": "n_fondos", "headerName": "# Fondos", "width": 110, "sortable": True},
        {"field": "patrimonio_MM$", "headerName": "AUM (miles M$)", "width": 150,
         "sortable": True},
        {"field": "rend_mediano", "headerName": "Rend Mediano %", "width": 150,
         "sortable": True,
         "cellStyle": {"function": f"params.value > {inflacion_12m} ? "
                                    f"{{'color': '{VERDE}', 'fontWeight': '600'}} : "
                                    f"{{'color': '{ROJO}', 'fontWeight': '600'}}"}},
        {"field": "rend_real_mediano", "headerName": "Rend Real %", "width": 130,
         "sortable": True,
         "cellStyle": {"function": f"params.value > 0 ? "
                                    f"{{'color': '{VERDE}'}} : "
                                    f"{{'color': '{ROJO}'}}"}},
        {"field": "pct_ganaron", "headerName": "% Le ganaron inf", "width": 160,
         "sortable": True},
        {"field": "rend_maximo", "headerName": "Top %", "width": 100},
        {"field": "rend_minimo", "headerName": "Peor %", "width": 100},
    ]
    return dag.AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={"resizable": True, "sortable": True},
        dashGridOptions={"pagination": True, "paginationPageSize": 15},
        style={"height": "500px"},
        className="ag-theme-alpine-dark",
    )


def tab_admins_layout():
    if df_ranking.empty:
        return html.Div("Sin datos", style={"color": TEXTO, "padding": "40px"})

    top3 = df_ranking.head(3)
    kpis = dbc.Row([
        kpi_card("#1 " + top3.iloc[0]["administradora"],
                 f"{top3.iloc[0]['rend_mediano']}%",
                 f"{top3.iloc[0]['n_fondos']} fondos · {top3.iloc[0]['pct_ganaron']}% ganan inf",
                 VERDE),
        kpi_card("Admins analizadas", f"{len(df_ranking)}",
                 "Con ≥3 fondos cada una"),
        kpi_card("AUM total", f"${df_ranking['patrimonio_MM$'].sum():.1f}MM$",
                 "Miles de millones de pesos"),
        kpi_card("Admins que ganan inf", f"{(df_ranking['rend_mediano'] > inflacion_12m).sum()}",
                 f"de {len(df_ranking)} analizadas"),
    ], className="g-3 mb-4")

    graficos = dbc.Row([
        dbc.Col(html.Div(dcc.Graph(
            figure=build_bar_admins(df_ranking),
            config={"displayModeBar": False}), style=CARD_STYLE), md=6),
        dbc.Col(html.Div(dcc.Graph(
            figure=build_scatter_admins(df_ranking),
            config={"displayModeBar": False}), style=CARD_STYLE), md=6),
    ], className="mb-4 g-3")

    tabla = html.Div([
        html.P("Detalle por administradora",
               style={"color": TEXTO2, "fontSize": "12px",
                      "textTransform": "uppercase", "marginBottom": "12px"}),
        build_grid_admins(df_ranking),
    ], style=CARD_STYLE)

    return html.Div([kpis, graficos, tabla])


# ══════════════════════════════════════════════
# TAB 4 — COMPARADOR
# ══════════════════════════════════════════════
def tab_comparador_layout():
    fondos_opciones = sorted(df_snapshot["fondo"].unique())
    return html.Div([
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondos a comparar (máx 4)",
                               style={"color": TEXTO2, "fontSize": "12px",
                                      "textTransform": "uppercase"}),
                    dcc.Dropdown(
                        id="comparador-fondos",
                        options=[{"label": f, "value": f} for f in fondos_opciones],
                        multi=True,
                        placeholder="Buscá y seleccioná fondos...",
                        style={"backgroundColor": CARD_BG},
                    ),
                ], md=8),
                dbc.Col([
                    html.Label("Días hacia atrás",
                               style={"color": TEXTO2, "fontSize": "12px",
                                      "textTransform": "uppercase"}),
                    dcc.Dropdown(
                        id="comparador-dias",
                        options=[{"label": f"{d} días", "value": d}
                                 for d in [15, 30, 60, 90]],
                        value=30, clearable=False,
                        style={"backgroundColor": CARD_BG},
                    ),
                ], md=2),
                dbc.Col([
                    html.Label(" ", style={"display": "block"}),
                    dbc.Button("Comparar", id="btn-comparar", color="primary",
                               className="w-100", style={"marginTop": "4px"}),
                ], md=2),
            ], className="g-3"),
            html.Div(
                "Tip: el comparador descarga series de a un día por llamada HTTP, por eso "
                "puede tardar 10-30s. Los datos quedan cacheados en SQLite para próximas consultas.",
                style={"color": TEXTO2, "fontSize": "11px", "marginTop": "8px",
                       "fontStyle": "italic"}
            ),
        ], style={**CARD_STYLE, "marginBottom": "24px"}),

        dcc.Loading(
            type="default",
            children=html.Div(
                id="comparador-contenido",
                children=html.Div(
                    "Seleccioná 2-4 fondos y apretá 'Comparar'.",
                    style={"color": TEXTO2, "textAlign": "center",
                           "padding": "80px", "fontStyle": "italic"}
                ),
                style=CARD_STYLE
            ),
        )
    ])


# ══════════════════════════════════════════════
# TAB 5 — SCORECARD
# ══════════════════════════════════════════════
def build_grid_scorecard(df):
    if df.empty:
        return dag.AgGrid(rowData=[], columnDefs=[])
    df_show = df.copy()
    df_show["patrimonio_M"] = (df_show["patrimonio"] / 1e6).round(1).fillna(0)

    col_defs = [
        {"field": "fondo", "headerName": "Fondo", "minWidth": 260,
         "filter": True, "pinned": "left"},
        {"field": "Riesgo", "headerName": "Riesgo", "width": 110, "filter": True,
         "pinned": "left"},
        {"field": "RiskScore", "headerName": "Score", "width": 90, "sortable": True,
         "cellStyle": {"function": "params.value >= 70 ? "
                                   f"{{'color': '{VERDE}', 'fontWeight': '700'}} : "
                                   "params.value >= 50 ? "
                                   f"{{'color': '{AMARILLO}'}} : "
                                   f"{{'color': '{ROJO}'}}"}},
        {"field": "tipo", "headerName": "Tipo", "width": 130, "filter": True},
        {"field": "administradora", "headerName": "Admin", "width": 160, "filter": True},
        {"field": "rendimiento_%", "headerName": "Rend %", "width": 100, "sortable": True},
        {"field": "rendimiento_real_%", "headerName": "Rend Real %", "width": 125, "sortable": True},
        {"field": "score_rendimiento", "headerName": "Perf", "width": 85},
        {"field": "score_consistencia", "headerName": "Consist", "width": 95},
        {"field": "score_tamano", "headerName": "Tamaño", "width": 90},
        {"field": "score_concentracion", "headerName": "Concentr", "width": 105},
        {"field": "patrimonio_M", "headerName": "AUM (M$)", "width": 120, "sortable": True},
    ]
    return dag.AgGrid(
        id="tabla-scorecard",
        rowData=df_show.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={"resizable": True, "sortable": True},
        dashGridOptions={"pagination": True, "paginationPageSize": 20,
                         "animateRows": True},
        style={"height": "600px"},
        className="ag-theme-alpine-dark",
    )


def tab_scorecard_layout():
    bajo  = int((df_scorecard["RiskScore"] >= 70).sum())
    medio = int((df_scorecard["RiskScore"].between(50, 70, inclusive="left")).sum())
    alto  = int((df_scorecard["RiskScore"] < 50).sum())
    kpis = dbc.Row([
        kpi_card("🟢 Riesgo bajo", f"{bajo}", "Score ≥ 70", VERDE),
        kpi_card("🟡 Riesgo medio", f"{medio}", "Score 50-70", AMARILLO),
        kpi_card("🔴 Riesgo alto", f"{alto}", "Score < 50", ROJO),
        kpi_card("Total evaluados", f"{len(df_scorecard)}",
                 "Con rendimiento anual disponible"),
    ], className="g-3 mb-4")

    explicacion = html.Div([
        html.P("Metodología del RiskScore",
               style={"color": TEXTO, "fontSize": "14px",
                      "fontWeight": "600", "marginBottom": "8px"}),
        html.P([
            "Ponderación inspirada en frameworks de Tech Risk:",
            html.Br(),
            "• Performance real (45%): rendimiento descontando inflación",
            html.Br(),
            "• Consistencia (25%): ¿le ganó a la inflación?",
            html.Br(),
            "• Tamaño/AUM (20%): fondos más chicos → más volátiles",
            html.Br(),
            "• Concentración (10%): penaliza fondos >5% del segmento",
        ], style={"color": TEXTO2, "fontSize": "12px", "margin": 0,
                  "lineHeight": "1.8"}),
    ], style={**CARD_STYLE, "marginBottom": "24px"})

    tabla = html.Div([
        html.P("Fondos ordenados por RiskScore (mayor = más atractivo)",
               style={"color": TEXTO2, "fontSize": "12px",
                      "textTransform": "uppercase", "marginBottom": "12px"}),
        build_grid_scorecard(df_scorecard),
    ], style=CARD_STYLE)

    return html.Div([kpis, explicacion, tabla])


# ══════════════════════════════════════════════
# LAYOUT PRINCIPAL
# ══════════════════════════════════════════════
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    title="FCI Argentina — Dashboard",
    suppress_callback_exceptions=True,
)

header = dbc.Row([
    dbc.Col([
        html.H2("📊 Fondos Comunes de Inversión",
                style={"color": TEXTO, "fontWeight": "700", "margin": "0"}),
        html.P(f"Argentina · Datos al {datetime.today().strftime('%d/%m/%Y')} "
               f"· Fuente: ArgentinaDatos / CAFCI",
               style={"color": TEXTO2, "fontSize": "13px", "margin": "4px 0 0 0"}),
    ]),
    dbc.Col([
        dbc.Badge(f"Inflación 12m: {inflacion_12m}%", color="warning",
                  className="me-2", style={"fontSize": "13px"}),
        dbc.Badge(f"{len(df_snapshot):,} fondos activos", color="secondary",
                  style={"fontSize": "13px"}),
    ], className="d-flex align-items-center justify-content-end"),
], className="mb-4")

tabs = dbc.Tabs([
    dbc.Tab(tab_resumen_layout(),  label="📊 Resumen",        tab_id="tab-resumen"),
    dbc.Tab(tab_portipo_layout(),  label="📈 Por Tipo",       tab_id="tab-tipo"),
    dbc.Tab(tab_admins_layout(),   label="🏢 Administradoras", tab_id="tab-admins"),
    dbc.Tab(tab_comparador_layout(), label="⚖️ Comparador",    tab_id="tab-comp"),
    dbc.Tab(tab_scorecard_layout(), label="🎯 Scorecard",      tab_id="tab-score"),
], active_tab="tab-resumen", className="mb-3")


# ══════════════════════════════════════════════
# FOOTER CON FUENTES Y DISCLAIMER
# ══════════════════════════════════════════════
def link_ext(texto, url):
    return html.A(texto, href=url, target="_blank",
                  style={"color": AZUL, "textDecoration": "none"})


footer = html.Div([
    html.Hr(style={"borderColor": BORDE, "marginTop": "32px", "marginBottom": "20px"}),
    dbc.Row([
        # Columna 1: fuentes de datos
        dbc.Col([
            html.P("Fuentes de datos",
                   style={"color": TEXTO, "fontSize": "12px", "fontWeight": "600",
                          "textTransform": "uppercase", "letterSpacing": "1px",
                          "marginBottom": "10px"}),
            html.Ul([
                html.Li([
                    link_ext("ArgentinaDatos API", "https://api.argentinadatos.com"),
                    html.Span(" — endpoints /fci, /inflacion, /dolares "
                              "(no requiere auth).",
                              style={"color": TEXTO2}),
                ]),
                html.Li([
                    link_ext("CAFCI", "https://www.cafci.org.ar/"),
                    html.Span(" — Cámara Argentina de FCI, emisor original "
                              "de los datos diarios.",
                              style={"color": TEXTO2}),
                ]),
                html.Li([
                    link_ext("CNV", "https://www.cnv.gov.ar/sitioWeb/FondosComunesInversion"),
                    html.Span(" — regulador del mercado de capitales.",
                              style={"color": TEXTO2}),
                ]),
                html.Li([
                    link_ext("INDEC", "https://www.indec.gob.ar/indec/web/Nivel3-Tema-3-5"),
                    html.Span(" — índice de precios al consumidor (IPC).",
                              style={"color": TEXTO2}),
                ]),
            ], style={"color": TEXTO, "fontSize": "12px", "lineHeight": "1.8",
                      "paddingLeft": "18px", "marginBottom": "0"}),
        ], md=5),

        # Columna 2: metodología breve
        dbc.Col([
            html.P("Metodología",
                   style={"color": TEXTO, "fontSize": "12px", "fontWeight": "600",
                          "textTransform": "uppercase", "letterSpacing": "1px",
                          "marginBottom": "10px"}),
            html.Ul([
                html.Li("Rendimiento nominal: (VCP_fin / VCP_inicio − 1) × 100, "
                        "punta a punta sobre días hábiles.",
                        style={"color": TEXTO2}),
                html.Li(["Rendimiento real (Fisher): ",
                         html.Code("((1 + nominal) / (1 + inflación) − 1)",
                                   style={"backgroundColor": BORDE, "padding": "1px 6px",
                                          "borderRadius": "3px", "color": TEXTO})],
                        style={"color": TEXTO2}),
                html.Li("Se excluyen fondos con patrimonio < $1M o con VCP "
                        "nominal (caparazones sin inversores reales).",
                        style={"color": TEXTO2}),
                html.Li("Outliers: se filtran rendimientos < −50% o > 200% "
                        "(errores de data o fondos liquidados).",
                        style={"color": TEXTO2}),
            ], style={"fontSize": "12px", "lineHeight": "1.8",
                      "paddingLeft": "18px", "marginBottom": "0"}),
        ], md=5),

        # Columna 3: meta
        dbc.Col([
            html.P("Info",
                   style={"color": TEXTO, "fontSize": "12px", "fontWeight": "600",
                          "textTransform": "uppercase", "letterSpacing": "1px",
                          "marginBottom": "10px"}),
            html.P([
                "Inflación 12m: ", html.Strong(f"{inflacion_12m}%",
                                                style={"color": AMARILLO}), html.Br(),
                "Fondos en BD: ", html.Strong(f"{len(df_snapshot):,}",
                                                style={"color": TEXTO}), html.Br(),
                "Actualizado: ", html.Strong(datetime.today().strftime("%d/%m/%Y"),
                                              style={"color": TEXTO}),
            ], style={"color": TEXTO2, "fontSize": "12px", "lineHeight": "1.8",
                      "marginBottom": "0"}),
        ], md=2),
    ], className="g-3"),

    # Disclaimer
    html.Div([
        html.P([
            html.Strong("Descargo: ", style={"color": AMARILLO}),
            "Este sitio tiene fines exclusivamente educativos e informativos. ",
            "No constituye asesoramiento financiero, recomendación de inversión, ",
            "ni oferta pública. La inversión en FCI conlleva riesgos; los ",
            "rendimientos pasados no garantizan resultados futuros. Las ",
            "decisiones de inversión son responsabilidad exclusiva del usuario, ",
            "quien debe consultar con un Agente de Colocación y Distribución ",
            "Integral de FCI matriculado en la CNV.",
        ], style={"color": TEXTO2, "fontSize": "11px", "marginBottom": "4px",
                  "lineHeight": "1.6"}),
        html.P([
            "Proyecto independiente · ",
            link_ext("Código en GitHub", "https://github.com/"),
            " · Construido con Dash + Plotly · No afiliado a CAFCI, CNV ni ",
            "ninguna administradora.",
        ], style={"color": TEXTO2, "fontSize": "11px", "marginBottom": "0",
                  "textAlign": "center", "fontStyle": "italic",
                  "marginTop": "12px", "paddingTop": "12px",
                  "borderTop": f"1px solid {BORDE}"}),
    ], style={"marginTop": "20px"}),
], style={"marginTop": "40px", "padding": "24px", "backgroundColor": CARD_BG,
          "borderRadius": "12px", "border": f"1px solid {BORDE}"})


app.layout = html.Div(
    style={"backgroundColor": BG, "minHeight": "100vh", "padding": "24px",
           "fontFamily": "Inter, sans-serif"},
    children=[header, tabs, footer]
)


# ══════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════
@callback(
    Output("grafico-histograma", "figure"),
    Output("grafico-torta",      "figure"),
    Output("contenedor-tabla",   "children"),
    Input("filtro-horizonte",    "value"),
    Input("filtro-rendimiento",  "value"),
)
def actualizar_resumen(horizontes, rend_min):
    df = df_rend_fija.copy()
    if rend_min is not None:
        df = df[df["rendimiento_%"] >= rend_min]
    if horizontes:
        df = df[df["horizonte"].isin(horizontes)]
    gana   = int((df["rendimiento_%"] > inflacion_12m).sum())
    pierde = len(df) - gana
    pct    = round(gana / len(df) * 100) if len(df) else 0
    return (
        build_histograma(df, inflacion_12m),
        build_torta(gana, pierde, pct),
        build_grid_resumen(df),
    )


@callback(
    Output("comparador-contenido", "children"),
    Input("btn-comparar", "n_clicks"),
    State("comparador-fondos", "value"),
    State("comparador-dias", "value"),
    prevent_initial_call=True,
)
def ejecutar_comparador(n_clicks, fondos, dias):
    if not fondos or len(fondos) < 2:
        return html.Div("Elegí al menos 2 fondos.",
                        style={"color": AMARILLO, "padding": "40px",
                               "textAlign": "center"})
    fondos = fondos[:4]  # cap a 4 para no abusar
    df = serie_comparativa(dl, fondos, dias_atras=dias, base_100=True)
    if df.empty:
        return html.Div("No se pudo reconstruir serie histórica "
                        "(API sin datos recientes).",
                        style={"color": ROJO, "padding": "40px",
                               "textAlign": "center"})

    fig = go.Figure()
    paleta = [AZUL, VERDE, AMARILLO, MAGENTA]
    for i, f in enumerate(fondos):
        sub = df[df["fondo"] == f].sort_values("fecha")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["fecha"], y=sub["vcp_base100"],
            mode="lines+markers",
            name=f[:40] + "…" if len(f) > 40 else f,
            line=dict(color=paleta[i % len(paleta)], width=2),
        ))
    fig = layout_plotly(fig, "Evolución VCP (base 100)")
    fig.update_yaxes(title="VCP normalizado (base 100)")
    fig.update_xaxes(title="Fecha")
    fig.update_layout(height=500,
                       legend=dict(orientation="h", y=-0.2,
                                   font_color=TEXTO2))

    # Tabla resumen
    resumen = df.groupby("fondo").apply(
        lambda g: pd.Series({
            "dias": len(g),
            "vcp_inicio": round(g["vcp"].iloc[0], 2),
            "vcp_fin":    round(g["vcp"].iloc[-1], 2),
            "rend_%":     round((g["vcp"].iloc[-1] / g["vcp"].iloc[0] - 1) * 100, 2),
        })
    ).reset_index()

    col_defs = [
        {"field": "fondo", "headerName": "Fondo", "minWidth": 300},
        {"field": "dias", "headerName": "Días"},
        {"field": "vcp_inicio", "headerName": "VCP inicio"},
        {"field": "vcp_fin", "headerName": "VCP fin"},
        {"field": "rend_%", "headerName": "Rendimiento %",
         "cellStyle": {"function": f"params.value > 0 ? "
                                    f"{{'color': '{VERDE}', 'fontWeight': '600'}} : "
                                    f"{{'color': '{ROJO}', 'fontWeight': '600'}}"}},
    ]
    tabla = dag.AgGrid(
        rowData=resumen.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={"resizable": True, "sortable": True},
        style={"height": "250px"},
        className="ag-theme-alpine-dark",
    )

    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Hr(style={"borderColor": BORDE}),
        html.P("Resumen", style={"color": TEXTO2, "fontSize": "12px",
                                  "textTransform": "uppercase"}),
        tabla,
    ])


# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("🚀 Dashboard corriendo en http://localhost:8050")
    app.run(debug=True, port=8050)