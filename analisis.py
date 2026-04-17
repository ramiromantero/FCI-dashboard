"""
ANALISIS - FCI Argentina
========================
Funciones de analisis puro (sin UI). Operan sobre los DataFrames que
expone DataLayer. Todas son idempotentes y no tocan SQLite.

Bloques:
    1. Rendimientos multi-tipo
    2. Ranking por administradora
    3. Risk Scorecard (Tech Risk style)
    4. Comparador de fondos
    5. Rendimiento real (descontando inflacion)
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional

import numpy as np
import pandas as pd

from data_layer import DataLayer, TIPOS_ENDPOINT

# Limites para filtrar outliers de rendimiento (Gainvest, fondos nuevos, etc.)
RENDIMIENTO_MIN = -50
RENDIMIENTO_MAX = 200

# Patrimonio minimo para que el fondo se considere "real" (en pesos).
# Con esto filtramos caparazones tipo "Superfondo Renta Global" que tienen
# VCP nominal 1000→2000 y patrimonio NaN.
PATRIMONIO_MIN = 1_000_000  # 1 millón de pesos


def _filtrar_fondos_reales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra fondos 'fantasma' / caparazones contables:
      - patrimonio NaN o muy chico
      - ccp NaN (sin cuotapartes emitidas)
      - VCP_inicio exactamente 1000.0 (valor nominal de lanzamiento)
    """
    if df.empty:
        return df
    mask = (
        df["patrimonio"].notna() &
        (df["patrimonio"] >= PATRIMONIO_MIN) &
        df.get("ccp", pd.Series([1]*len(df), index=df.index)).notna()
    )
    # Si hay vcp_inicio (modo rendimiento), filtrar valores nominales perfectos
    if "vcp_inicio" in df.columns:
        # VCP exactamente redondo en múltiplos de 1000 y fondo sin patrimonio → sospechoso
        vcp_redondo = (df["vcp_inicio"] % 1000 == 0) & (df["vcp_inicio"] <= 10000)
        mask = mask & ~vcp_redondo
    return df[mask].copy()


# ──────────────────────────────────────────────────────────────
# 1. RENDIMIENTOS MULTI-TIPO
# ──────────────────────────────────────────────────────────────
def rendimiento_anual(dl: DataLayer, tipo: str,
                      dias_atras: int = 365,
                      filtrar_outliers: bool = True) -> pd.DataFrame:
    """
    Calcula rendimiento punta a punta comparando VCP de hoy vs hace N dias.
    Funciona para cualquier tipo: 'Renta Fija', 'Renta Variable',
    'Mercado Dinero', 'Renta Mixta'.
    """
    df_fin = dl.fetch_snapshot_api([tipo])
    if df_fin.empty:
        return pd.DataFrame()

    fecha_fin = datetime.strptime(df_fin["fecha"].iloc[0], "%Y-%m-%d").date()
    target    = fecha_fin - timedelta(days=dias_atras)
    df_ini, fecha_ini = dl.fetch_fecha_habil_api(tipo, target, lookback_dias=15)
    if df_ini.empty:
        return pd.DataFrame()

    df_i = df_ini[["fondo", "vcp"]].rename(columns={"vcp": "vcp_inicio"})
    df_f = df_fin[["fondo", "vcp", "patrimonio", "horizonte",
                   "administradora", "tipo"]].rename(columns={"vcp": "vcp_fin"})

    df = pd.merge(df_i, df_f, on="fondo", how="inner")
    df["rendimiento_%"] = ((df["vcp_fin"] / df["vcp_inicio"]) - 1) * 100
    df["rendimiento_%"] = df["rendimiento_%"].round(2)
    df["fecha_inicio"] = fecha_ini
    df["fecha_fin"]    = df_fin["fecha"].iloc[0]
    df["dias"]         = dias_atras

    if filtrar_outliers:
        df = df[(df["rendimiento_%"] <= RENDIMIENTO_MAX) &
                (df["rendimiento_%"] >= RENDIMIENTO_MIN)]
        df = _filtrar_fondos_reales(df)

    return df.sort_values("rendimiento_%", ascending=False).reset_index(drop=True)


def rendimiento_todos_tipos(dl: DataLayer,
                             dias_atras: int = 365,
                             filtrar_outliers: bool = True) -> pd.DataFrame:
    """Rendimiento anual de TODOS los tipos concatenados."""
    dfs = []
    for tipo in TIPOS_ENDPOINT.keys():
        df = rendimiento_anual(dl, tipo, dias_atras, filtrar_outliers)
        if not df.empty:
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def agregar_rendimiento_real(df: pd.DataFrame, inflacion_pct: float) -> pd.DataFrame:
    """
    Rendimiento real = ((1 + nominal/100) / (1 + inflacion/100) - 1) * 100
    (Formula de Fisher, correcta para deflactar.)
    """
    if df.empty:
        return df
    df = df.copy()
    df["rendimiento_real_%"] = (
        ((1 + df["rendimiento_%"] / 100) / (1 + inflacion_pct / 100) - 1) * 100
    ).round(2)
    df["gana_inflacion"] = df["rendimiento_%"] > inflacion_pct
    return df


# ──────────────────────────────────────────────────────────────
# 2. RANKING POR ADMINISTRADORA
# ──────────────────────────────────────────────────────────────
def ranking_administradoras(df_rend: pd.DataFrame,
                             inflacion_pct: float,
                             min_fondos: int = 3) -> pd.DataFrame:
    """
    Agrupa rendimientos por administradora y calcula metricas agregadas.
    Filtra administradoras con muy pocos fondos para evitar ruido.
    """
    if df_rend.empty:
        return pd.DataFrame()

    g = df_rend.groupby("administradora").agg(
        n_fondos=("fondo", "count"),
        rend_mediano=("rendimiento_%", "median"),
        rend_promedio=("rendimiento_%", "mean"),
        rend_maximo=("rendimiento_%", "max"),
        rend_minimo=("rendimiento_%", "min"),
        patrimonio_total=("patrimonio", "sum"),
    ).reset_index()

    g = g[g["n_fondos"] >= min_fondos].copy()
    g["ganaron_inflacion"] = g.apply(
        lambda r: int(((df_rend["administradora"] == r["administradora"]) &
                        (df_rend["rendimiento_%"] > inflacion_pct)).sum()),
        axis=1
    )
    g["pct_ganaron"] = (g["ganaron_inflacion"] / g["n_fondos"] * 100).round(0)
    g["rend_real_mediano"] = (
        ((1 + g["rend_mediano"] / 100) / (1 + inflacion_pct / 100) - 1) * 100
    ).round(2)

    for col in ("rend_mediano", "rend_promedio", "rend_maximo", "rend_minimo"):
        g[col] = g[col].round(2)
    g["patrimonio_total"] = (g["patrimonio_total"] / 1e9).round(2)  # en miles de millones
    g = g.rename(columns={"patrimonio_total": "patrimonio_MM$"})

    return g.sort_values("rend_mediano", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────
# 3. RISK SCORECARD (Tech Risk style)
# ──────────────────────────────────────────────────────────────
def risk_scorecard(df_rend: pd.DataFrame,
                   df_snapshot: pd.DataFrame,
                   inflacion_pct: float) -> pd.DataFrame:
    """
    Genera un scorecard por fondo con metricas inspiradas en control framework:
      - performance: rendimiento nominal y real
      - size: patrimonio
      - liquidity: ccp * vcp vs patrimonio total (sanity check)
      - persistence: si le gana a inflacion (flag)
      - concentration: % del patrimonio del fondo vs patrimonio total del tipo

    Cada metrica se convierte en score 0-100; el RiskScore final es el promedio
    ponderado. Inspiracion: controls framework de auditoria IT (likelihood + impact).
    """
    if df_rend.empty or df_snapshot.empty:
        return pd.DataFrame()

    df = df_rend.copy()

    # Rendimiento real
    df = agregar_rendimiento_real(df, inflacion_pct)

    # Patrimonio total del tipo del fondo (para medir concentracion)
    tipo_pat = df_snapshot.groupby("tipo")["patrimonio"].sum().to_dict()
    df["pat_total_tipo"] = df["tipo"].map(tipo_pat)
    df["concentracion_%"] = (df["patrimonio"] / df["pat_total_tipo"] * 100).round(3)

    # ───── Score components (0-100) ─────
    # 1. Score de rendimiento real: -20%→0, 0%→50, +20%→100, clipped
    df["score_rendimiento"] = np.clip(
        50 + df["rendimiento_real_%"] * 2.5, 0, 100
    ).round(1)

    # 2. Score de tamaño: fondos muy chicos → riesgo. Usamos log(patrimonio)
    #    patrimonio < 100M → 0, > 100B → 100
    pat_log = np.log10(df["patrimonio"].fillna(1).clip(lower=1))
    df["score_tamano"] = np.clip(
        (pat_log - 8) / (11 - 8) * 100, 0, 100
    ).round(1)

    # 3. Score de concentracion: fondos > 5% del tipo → penalizamos (muy concentrados en cartera)
    df["score_concentracion"] = np.where(
        df["concentracion_%"].fillna(0) > 5,
        np.clip(100 - df["concentracion_%"] * 5, 0, 100),
        100
    ).round(1)

    # 4. Score "consistencia": binary flag de si le gano a la inflacion
    df["score_consistencia"] = df["gana_inflacion"].astype(int) * 100

    # Ponderacion
    pesos = {
        "score_rendimiento":  0.45,
        "score_consistencia": 0.25,
        "score_tamano":       0.20,
        "score_concentracion": 0.10,
    }
    df["RiskScore"] = sum(df[k] * v for k, v in pesos.items())
    df["RiskScore"] = df["RiskScore"].round(1)

    # Semaforo
    def semaforo(s):
        if s >= 70: return "🟢 Bajo"
        if s >= 50: return "🟡 Medio"
        return "🔴 Alto"
    df["Riesgo"] = df["RiskScore"].apply(semaforo)

    cols_orden = [
        "fondo", "tipo", "administradora", "horizonte", "patrimonio",
        "rendimiento_%", "rendimiento_real_%", "concentracion_%",
        "score_rendimiento", "score_consistencia", "score_tamano",
        "score_concentracion", "RiskScore", "Riesgo",
    ]
    return df[cols_orden].sort_values("RiskScore", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────
# 4. COMPARADOR DE FONDOS
# ──────────────────────────────────────────────────────────────
def serie_comparativa(dl: DataLayer, fondos: list[str],
                       dias_atras: int = 90,
                       base_100: bool = True) -> pd.DataFrame:
    """
    Toma N fondos, reconstruye su serie de VCP de los ultimos `dias_atras`
    dias habiles bajando datos de la API (usando SQLite como cache).

    Si base_100=True, cada serie se normaliza a 100 en el primer dia
    (asi se comparan a pesar de tener VCPs distintos).
    """
    if not fondos:
        return pd.DataFrame()

    # Primero saco el tipo de cada fondo del snapshot mas reciente
    snap = dl.snapshot_mas_reciente()
    info = snap[snap["fondo"].isin(fondos)][["fondo", "tipo"]].drop_duplicates()

    # Bajo snapshot de cada uno de los ultimos N dias habiles
    fecha_fin = date.today()
    fechas = []
    d = fecha_fin
    while len(fechas) < dias_atras:
        # salteamos sabados/domingos
        if d.weekday() < 5:
            fechas.append(d)
        d -= timedelta(days=1)
        if (fecha_fin - d).days > dias_atras * 2:
            break  # safety

    # Por cada (fondo, tipo) buscamos en DB primero, completamos con API
    filas = []
    for _, row in info.iterrows():
        fondo, tipo = row["fondo"], row["tipo"]
        # Forzamos que esten en DB (baja las que falten)
        dl.completar_serie_api(fondo, tipo, fechas[:min(20, len(fechas))])
        # Ahora leemos de DB
        df = dl.serie_historica_fondo(fondo)
        df = df.copy()
        df["fondo"] = fondo
        filas.append(df)

    if not filas:
        return pd.DataFrame()
    df_all = pd.concat(filas, ignore_index=True)
    df_all["fecha"] = pd.to_datetime(df_all["fecha"])
    df_all = df_all.sort_values(["fondo", "fecha"])

    if base_100 and not df_all.empty:
        df_all["vcp_base100"] = df_all.groupby("fondo")["vcp"].transform(
            lambda s: s / s.iloc[0] * 100
        )
    return df_all


# ──────────────────────────────────────────────────────────────
# 5. RENDIMIENTO VS DOLAR
# ──────────────────────────────────────────────────────────────
def rendimiento_dolar(dl: DataLayer, tipo_dolar: str = "blue",
                       dias_atras: int = 365) -> float:
    """Rendimiento del dolar como comparacion adicional para benchmark."""
    df = dl.dolar(tipos=(tipo_dolar,))
    if df.empty:
        return 0.0
    df = df[df["tipo"] == tipo_dolar].copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha")
    fin = df.iloc[-1]["venta"]
    target = df["fecha"].max() - pd.Timedelta(days=dias_atras)
    ini_row = df[df["fecha"] <= target]
    if ini_row.empty:
        return 0.0
    ini = ini_row.iloc[-1]["venta"]
    return round((fin / ini - 1) * 100, 2)


# ──────────────────────────────────────────────────────────────
# Sanity check cli
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    dl = DataLayer()
    inf = dl.inflacion_acumulada()
    print(f"💰 Inflación 12m: {inf}%")

    df = rendimiento_todos_tipos(dl, 365)
    df = agregar_rendimiento_real(df, inf)
    print(f"\n📈 Rendimientos por tipo:")
    print(df.groupby("tipo")["rendimiento_%"].describe().round(2))

    print(f"\n🏢 Top 10 administradoras por mediana:")
    rank = ranking_administradoras(df, inf)
    print(rank.head(10).to_string(index=False))

    print(f"\n🎯 Risk scorecard (top 10 por RiskScore):")
    snap = dl.snapshot_mas_reciente()
    sc = risk_scorecard(df, snap, inf)
    print(sc.head(10)[["fondo", "tipo", "RiskScore", "Riesgo"]].to_string(index=False))