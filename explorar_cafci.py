"""
EXPLORACIÓN DE FCIs - ArgentinaDatos API
==========================================
Correr con: python explorar_fci.py
Requiere:   pip install requests pandas

Qué hace:
1. Trae fondos de renta fija, renta variable, mercado de dinero
2. Trae inflación histórica
3. Calcula qué fondos le ganaron a la inflación
4. Muestra los datos en tablas para explorar
"""

import requests
import pandas as pd
from datetime import datetime, timedelta

BASE = "https://api.argentinadatos.com"

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get(endpoint):
    url = BASE + endpoint
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"  ❌ Error {r.status_code} en {endpoint}")
        return None


def mostrar(df, titulo, n=10):
    print(f"\n{'='*55}")
    print(f"  {titulo}")
    print(f"{'='*55}")
    print(df.head(n).to_string(index=False))
    print(f"  ... {len(df)} registros totales")


# ─────────────────────────────────────────────
# 1. TRAER FONDOS (último día disponible)
# ─────────────────────────────────────────────
def traer_fondos():
    tipos = {
        "Renta Fija":      "/v1/finanzas/fci/rentaFija/ultimo",
        "Renta Variable":  "/v1/finanzas/fci/rentaVariable/ultimo",
        "Mercado Dinero":  "/v1/finanzas/fci/mercadoDinero/ultimo",
        "Renta Mixta":     "/v1/finanzas/fci/rentaMixta/ultimo",
        "Otros":           "/v1/finanzas/fci/otros/ultimo",
    }

    dfs = []
    for tipo, endpoint in tipos.items():
        print(f"  Trayendo {tipo}...")
        data = get(endpoint)
        if data:
            df = pd.DataFrame(data)
            df["tipo"] = tipo
            dfs.append(df)
            print(f"    ✅ {len(df)} fondos")

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return None


# ─────────────────────────────────────────────
# 2. TRAER INFLACIÓN MENSUAL
# ─────────────────────────────────────────────
def traer_inflacion():
    print("  Trayendo inflación mensual...")
    data = get("/v1/finanzas/indices/inflacion")
    if data:
        df = pd.DataFrame(data)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.sort_values("fecha")
        print(f"    ✅ {len(df)} meses de datos")
        return df
    return None


# ─────────────────────────────────────────────
# 3. INFLACIÓN ACUMULADA (últimos N meses)
# ─────────────────────────────────────────────
def calcular_inflacion_acumulada(df_inflacion, meses=12):
    """
    Calcula la inflación acumulada en los últimos N meses.
    La inflación se acumula multiplicando (1 + tasa/100) mes a mes.
    """
    ultimos = df_inflacion.tail(meses).copy()
    acumulada = 1
    for _, row in ultimos.iterrows():
        acumulada *= (1 + row["valor"] / 100)
    return round((acumulada - 1) * 100, 2)


# ─────────────────────────────────────────────
# 4. TRAER DÓLAR HISTÓRICO
# ─────────────────────────────────────────────
def traer_dolar():
    print("  Trayendo cotizaciones del dólar...")
    # Tipos disponibles: oficial, blue, bolsa, contadoconliqui, mayorista, cripto
    tipos = ["oficial", "blue", "bolsa"]
    dfs = []
    for tipo in tipos:
        data = get(f"/v1/cotizaciones/dolares/{tipo}")
        if data:
            df = pd.DataFrame(data)
            df["tipo"] = tipo
            dfs.append(df)
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        df_total["fecha"] = pd.to_datetime(df_total["fecha"])
        print(f"    ✅ Datos de dólar cargados")
        return df_total
    return None


# ─────────────────────────────────────────────
# 5. ANÁLISIS: ¿qué fondos le ganaron a la inflación?
# ─────────────────────────────────────────────
def analisis_vs_inflacion(df_fondos, inflacion_acumulada_pct):
    """
    Compara el rendimiento de cada fondo contra la inflación acumulada.
    
    IMPORTANTE: el VCP (valor cuotaparte) es el precio de una cuotaparte hoy.
    Para saber el rendimiento necesitaríamos el VCP hace 12 meses también.
    Por ahora exploramos los datos disponibles y vemos qué podemos calcular.
    """
    print(f"\n📊 Inflación acumulada últimos 12 meses: {inflacion_acumulada_pct}%")
    print(f"\nCampos disponibles en los datos de fondos:")
    print(f"  {list(df_fondos.columns)}")
    
    print(f"\nEjemplo de un fondo:")
    print(df_fondos.iloc[0].to_string())
    
    # Ver distribución de tipos
    print(f"\n📦 Fondos por tipo:")
    print(df_fondos["tipo"].value_counts().to_string())
    
    # Ver fondos con mayor patrimonio
    if "patrimonio" in df_fondos.columns:
        df_top = df_fondos.nlargest(10, "patrimonio")[["fondo", "tipo", "patrimonio", "vcp"]]
        mostrar(df_top, "Top 10 fondos por patrimonio")
    
    return df_fondos


# ─────────────────────────────────────────────
# 6. HISTÓRICO: rendimiento anual de un tipo de fondo
# ─────────────────────────────────────────────
def get_fecha_habil(tipo_endpoint, fecha_target, buscar_dias=10):
    """Busca el día hábil más cercano hacia atrás. API usa YYYY/MM/DD."""
    for i in range(buscar_dias):
        fecha = fecha_target - timedelta(days=i)
        fecha_str = fecha.strftime("%Y/%m/%d")
        data = get(f"/v1/finanzas/fci/{tipo_endpoint}/{fecha_str}")
        if data:
            reales = [x for x in data if x.get("vcp") is not None]
            if reales:
                print(f"   Fecha hábil encontrada: {fecha_str}")
                return data, fecha_str
    return None, None


def historico_fondo(tipo_endpoint):
    """
    Calcula rendimiento anual de todos los fondos de un tipo.
    Compara vcp de hace 1 año vs vcp actual.
    """
    # Paso 1: último dato disponible → saber la fecha real de hoy
    data_fin = get(f"/v1/finanzas/fci/{tipo_endpoint}/ultimo")
    if not data_fin:
        return None

    df_fin = pd.DataFrame(data_fin)
    df_fin = df_fin[df_fin["fecha"].notna() & df_fin["vcp"].notna()].copy()

    fecha_fin_str = df_fin["fecha"].iloc[0]
    fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d")

    print(f"\n📅 Calculando rendimiento {tipo_endpoint}")
    print(f"   Fecha fin: {fecha_fin_str}")

    # Paso 2: buscar día hábil de hace 1 año
    fecha_inicio_aprox = fecha_fin - timedelta(days=365)
    print(f"   Buscando día hábil cercano a {fecha_inicio_aprox.strftime('%Y-%m-%d')}...")
    data_inicio, fecha_inicio_str = get_fecha_habil(tipo_endpoint, fecha_inicio_aprox)

    if not data_inicio:
        print("  No se encontró fecha hábil de inicio")
        return None

    print(f"   Período: {fecha_inicio_str} → {fecha_fin_str}")

    df_inicio = pd.DataFrame(data_inicio)
    df_inicio = df_inicio[df_inicio["fecha"].notna() & df_inicio["vcp"].notna()].copy()

    # Paso 3: merge y calcular rendimiento
    df_i = df_inicio[["fondo", "vcp"]].rename(columns={"vcp": "vcp_inicio"})
    df_f = df_fin[["fondo", "vcp", "patrimonio", "horizonte"]].rename(columns={"vcp": "vcp_fin"})

    df = pd.merge(df_i, df_f, on="fondo", how="inner")
    df["rendimiento_%"] = ((df["vcp_fin"] / df["vcp_inicio"]) - 1) * 100
    df["rendimiento_%"] = df["rendimiento_%"].round(2)
    df = df.sort_values("rendimiento_%", ascending=False)

    print(f"   Fondos con datos en ambas fechas: {len(df)}")
    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    
    print("=" * 55)
    print("  EXPLORACIÓN FCI - ArgentinaDatos")
    print("=" * 55)
    
    # 1. Traer todos los fondos de hoy
    print("\n🏦 Cargando fondos...")
    df_fondos = traer_fondos()
    
    # 2. Traer inflación
    print("\n📈 Cargando inflación...")
    df_inflacion = traer_inflacion()
    
    # 3. Calcular inflación acumulada últimos 12 meses
    inflacion_12m = calcular_inflacion_acumulada(df_inflacion, meses=12)
    
    # 4. Análisis básico (filtrar filas agregadas sin vcp real)
    if df_fondos is not None:
        df_fondos = df_fondos[df_fondos["vcp"].notna()].copy()
        print(f"\n  Fondos con datos completos (vcp real): {len(df_fondos)}")
        analisis_vs_inflacion(df_fondos, inflacion_12m)
    
    # 5. Rendimiento histórico de renta fija (último año)
    print(f"\n📊 Calculando rendimiento renta fija último año...")
    df_rendimiento = historico_fondo("rentaFija")
    
    if df_rendimiento is not None:
        # Separar outliers antes del análisis
        df_normales  = df_rendimiento[
            (df_rendimiento["rendimiento_%"] <= 200) &
            (df_rendimiento["rendimiento_%"] >= -50)
        ].copy()
        df_outliers  = df_rendimiento[
            (df_rendimiento["rendimiento_%"] > 200) |
            (df_rendimiento["rendimiento_%"] < -50)
        ].copy()

        print(f"\n  Fondos normales (entre -50% y +200%): {len(df_normales)}")
        print(f"  Outliers descartados del análisis:    {len(df_outliers)}")

        print(f"\n⚠️  Outliers (para investigar aparte):")
        print(df_outliers[["fondo", "vcp_inicio", "vcp_fin", "rendimiento_%"]].to_string(index=False))

        print(f"\n🏆 Top 10 fondos RENTA FIJA - mejor rendimiento (sin outliers):")
        print(df_normales.head(10)[["fondo", "horizonte", "patrimonio", "rendimiento_%"]].to_string(index=False))

        print(f"\n📉 Peores 5 fondos RENTA FIJA (sin outliers):")
        print(df_normales.tail(5)[["fondo", "horizonte", "patrimonio", "rendimiento_%"]].to_string(index=False))

        # Análisis vs inflación — solo con fondos normales
        ganadores = df_normales[df_normales["rendimiento_%"] > inflacion_12m]
        perdedores = df_normales[df_normales["rendimiento_%"] <= inflacion_12m]

        print(f"\n{'='*55}")
        print(f"  INFLACIÓN ÚLTIMOS 12 MESES:           {inflacion_12m}%")
        print(f"  Fondos normales analizados:           {len(df_normales)}")
        print(f"  Fondos que le GANARON a la inflación: {len(ganadores)} ({round(len(ganadores)/len(df_normales)*100)}%)")
        print(f"  Fondos que NO le ganaron:             {len(perdedores)} ({round(len(perdedores)/len(df_normales)*100)}%)")
        print(f"  Rendimiento promedio:                 {df_normales['rendimiento_%'].mean():.2f}%")
        print(f"  Rendimiento mediano:                  {df_normales['rendimiento_%'].median():.2f}%")
        print(f"{'='*55}")

        # ── GRÁFICOS ──────────────────────────────
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("Fondos de Renta Fija - Rendimiento Anual vs Inflación", fontsize=14, fontweight="bold")

        # ── Gráfico 1: histograma de rendimientos ──
        ax1 = axes[0]
        color_ganador = "#2ecc71"
        color_perdedor = "#e74c3c"

        rend = df_normales["rendimiento_%"]
        bins = np.arange(rend.min() - 5, rend.max() + 5, 5)

        for b in range(len(bins) - 1):
            mask = (rend >= bins[b]) & (rend < bins[b+1])
            color = color_ganador if bins[b] >= inflacion_12m else color_perdedor
            ax1.bar(bins[b], mask.sum(), width=4.5, color=color, alpha=0.8, edgecolor="white")

        ax1.axvline(inflacion_12m, color="black", linewidth=2, linestyle="--", label=f"Inflación {inflacion_12m}%")
        ax1.axvline(rend.median(), color="orange", linewidth=1.5, linestyle=":", label=f"Mediana {rend.median():.1f}%")

        ganador_patch  = mpatches.Patch(color=color_ganador, label=f"Le ganan ({len(ganadores)} fondos, 29%)")
        perdedor_patch = mpatches.Patch(color=color_perdedor, label=f"No le ganan ({len(perdedores)} fondos, 71%)")
        ax1.legend(handles=[ganador_patch, perdedor_patch,
                             mpatches.Patch(color="black", label=f"Inflación {inflacion_12m}%"),
                             mpatches.Patch(color="orange", label=f"Mediana {rend.median():.1f}%")])

        ax1.set_xlabel("Rendimiento anual (%)")
        ax1.set_ylabel("Cantidad de fondos")
        ax1.set_title("Distribución de rendimientos")

        # ── Gráfico 2: torta ganadores vs perdedores ──
        ax2 = axes[1]
        labels = [f"Ganaron a inflación\n454 fondos (29%)", f"No ganaron\n1089 fondos (71%)"]
        sizes  = [len(ganadores), len(perdedores)]
        colors = [color_ganador, color_perdedor]
        explode = (0.05, 0)
        ax2.pie(sizes, labels=labels, colors=colors, explode=explode,
                autopct="%1.0f%%", startangle=90,
                textprops={"fontsize": 11}, pctdistance=0.6)
        ax2.set_title(f"¿Le ganaron a la inflación ({inflacion_12m}%)?")

        plt.tight_layout()
        plt.savefig("rendimiento_vs_inflacion.png", dpi=150, bbox_inches="tight")
        print("✅ Gráfico guardado en rendimiento_vs_inflacion.png")
        plt.show()
    
    # 6. Guardar fondos completos
    if df_fondos is not None:
        df_fondos.to_csv("fondos_hoy.csv", index=False)
        print("✅ Guardado en fondos_hoy.csv")
        print(f"   Columnas: {list(df_fondos.columns)}")
    
    print("\n✅ Exploración completa.")