"""
DATA LAYER - FCI Argentina
==========================
Capa unica de acceso a datos:
  - Baja datos de ArgentinaDatos API
  - Cachea en SQLite (fci.db) para acumular historico
  - Expone DataFrames limpios al resto del proyecto

Uso tipico:
    from data_layer import DataLayer
    dl = DataLayer()
    df_hoy = dl.snapshot_mas_reciente()
    df_rend = dl.rendimiento_anual(tipo="Renta Fija")

Primera corrida: va solo a la API.
Corridas siguientes: primero revisa SQLite, solo pega a la API si falta.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd
import requests

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
BASE_URL = "https://api.argentinadatos.com"
DB_PATH  = Path(__file__).parent / "fci.db"

TIPOS_ENDPOINT = {
    "Renta Fija":     "rentaFija",
    "Renta Variable": "rentaVariable",
    "Mercado Dinero": "mercadoDinero",
    "Renta Mixta":    "rentaMixta",
}

# Lista curada de administradoras. La matcheamos contra el nombre del fondo
# porque la API no devuelve el campo "administradora" por separado.
ADMINS_CONOCIDAS = [
    "1810", "1822", "Adcap", "Allaria", "Alpha", "Argenfunds", "Axis",
    "BAVSA", "Balanz", "CMA", "Champaquí", "Champaqui", "Cocos", "Compass",
    "Consultatio", "Delta", "Dracma", "FBA", "Fima", "First", "Fundcorp",
    "Gainvest", "Galileo", "Gestionar", "IAM", "ICBC", "IEB", "MAF",
    "MEGAQM", "Max", "Megainver", "Novus", "Optimum", "Parakeet",
    "Pellegrini", "Pionero", "Premier", "Quinquela", "SBS", "ST", "Santander",
    "Schroder", "Superfondo", "Tandem", "Toronto", "Valiant", "Wise", "Zofingen",
]

# Alias: mapeo de token que aparece en el nombre → nombre "bonito" de la admin
ADMIN_ALIAS = {
    "1822": "1822 (Banco Provincia)",
    "1810": "1810",
    "FBA": "FBA (BBVA)",
    "Fima": "Fima (Galicia)",
    "Max": "Max (Macro)",
    "Pellegrini": "Pellegrini (Nación)",
    "Superfondo": "Superfondo (ICBC)",
    "Toronto": "Toronto Trust",
    "Champaqui": "Champaquí",
}


# ──────────────────────────────────────────────────────────────
# HTTP
# ──────────────────────────────────────────────────────────────
def _api_get(endpoint: str, timeout: int = 15):
    """GET crudo contra ArgentinaDatos. Devuelve json o None."""
    try:
        r = requests.get(BASE_URL + endpoint, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        return None
    return None


# ──────────────────────────────────────────────────────────────
# SCHEMA SQLite
# ──────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS fondos_snapshot (
    fecha       TEXT    NOT NULL,
    tipo        TEXT    NOT NULL,
    fondo       TEXT    NOT NULL,
    administradora TEXT,
    vcp         REAL,
    ccp         REAL,
    patrimonio  REAL,
    horizonte   TEXT,
    tna         REAL,
    tea         REAL,
    PRIMARY KEY (fecha, fondo)
);
CREATE INDEX IF NOT EXISTS idx_snap_fondo  ON fondos_snapshot(fondo);
CREATE INDEX IF NOT EXISTS idx_snap_fecha  ON fondos_snapshot(fecha);
CREATE INDEX IF NOT EXISTS idx_snap_admin  ON fondos_snapshot(administradora);

CREATE TABLE IF NOT EXISTS inflacion (
    fecha TEXT PRIMARY KEY,
    valor REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dolar (
    fecha  TEXT NOT NULL,
    tipo   TEXT NOT NULL,
    compra REAL,
    venta  REAL,
    PRIMARY KEY (fecha, tipo)
);
"""


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def extraer_administradora(nombre_fondo: str) -> str:
    """
    Heuristica: tomo el primer token del nombre del fondo y lo comparo
    contra la lista curada. Si no matchea, devuelvo el primer token
    igual (asi no perdemos datos).
    """
    if not nombre_fondo:
        return "Desconocida"
    primer_token = nombre_fondo.strip().split(" ")[0]
    # Normalizar acentos básicos
    primer_norm = primer_token.replace("í", "i").replace("á", "a")
    for admin in ADMINS_CONOCIDAS:
        admin_norm = admin.replace("í", "i").replace("á", "a")
        if primer_norm.lower() == admin_norm.lower():
            return ADMIN_ALIAS.get(admin, admin)
    return primer_token


def _limpiar_df_fondos(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Filtra filas agregadas (sin vcp/fecha) y agrega columnas derivadas."""
    if df.empty:
        return df
    df = df[df["vcp"].notna() & df["fecha"].notna()].copy()
    df["tipo"] = tipo
    df["administradora"] = df["fondo"].apply(extraer_administradora)
    # Asegurar columnas opcionales
    for col in ("tna", "tea", "patrimonio", "ccp", "horizonte"):
        if col not in df.columns:
            df[col] = None
    return df


# ──────────────────────────────────────────────────────────────
# DATA LAYER
# ──────────────────────────────────────────────────────────────
class DataLayer:
    """
    Clase fachada. Mantiene la conexion a SQLite y expone metodos limpios.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_db()

    # ───── internals ─────
    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ───── snapshot diario ─────
    def fetch_snapshot_api(self, tipos: Optional[Iterable[str]] = None) -> pd.DataFrame:
        """Baja todos los tipos desde la API en una sola llamada por tipo."""
        tipos = tipos or list(TIPOS_ENDPOINT.keys())
        dfs = []
        for tipo in tipos:
            ep = TIPOS_ENDPOINT[tipo]
            data = _api_get(f"/v1/finanzas/fci/{ep}/ultimo")
            if data:
                dfs.append(_limpiar_df_fondos(pd.DataFrame(data), tipo))
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    def fetch_fecha_api(self, tipo: str, fecha: date) -> pd.DataFrame:
        """Baja datos de una fecha puntual para un tipo."""
        ep = TIPOS_ENDPOINT[tipo]
        fecha_str = fecha.strftime("%Y/%m/%d")
        data = _api_get(f"/v1/finanzas/fci/{ep}/{fecha_str}")
        if not data:
            return pd.DataFrame()
        return _limpiar_df_fondos(pd.DataFrame(data), tipo)

    def fetch_fecha_habil_api(self, tipo: str, target: date,
                              lookback_dias: int = 10) -> tuple[pd.DataFrame, Optional[str]]:
        """Busca el dia habil mas cercano hacia atras."""
        for i in range(lookback_dias):
            f = target - timedelta(days=i)
            df = self.fetch_fecha_api(tipo, f)
            if not df.empty:
                return df, df["fecha"].iloc[0]
        return pd.DataFrame(), None

    def guardar_snapshot(self, df: pd.DataFrame) -> int:
        """Upsert del snapshot en SQLite. Devuelve filas insertadas/actualizadas."""
        if df.empty:
            return 0
        cols = ["fecha", "tipo", "fondo", "administradora", "vcp", "ccp",
                "patrimonio", "horizonte", "tna", "tea"]
        df_ins = df.reindex(columns=cols).copy()
        with self._conn() as c:
            cur = c.cursor()
            sql = """INSERT OR REPLACE INTO fondos_snapshot
                     (fecha, tipo, fondo, administradora, vcp, ccp,
                      patrimonio, horizonte, tna, tea)
                     VALUES (?,?,?,?,?,?,?,?,?,?)"""
            cur.executemany(sql, df_ins.itertuples(index=False, name=None))
            return cur.rowcount

    def snapshot_diario(self, force_api: bool = False) -> pd.DataFrame:
        """
        Snapshot de hoy (o lo mas reciente).
        Si force_api=False y ya hay snapshot de hoy en DB, devuelve ese.
        """
        hoy_iso = date.today().isoformat()
        if not force_api:
            df = self._query(
                "SELECT * FROM fondos_snapshot WHERE fecha = ?", (hoy_iso,)
            )
            if not df.empty:
                return df
        df_api = self.fetch_snapshot_api()
        if df_api.empty:
            return pd.DataFrame()
        self.guardar_snapshot(df_api)
        return df_api

    def snapshot_mas_reciente(self) -> pd.DataFrame:
        """
        Devuelve el snapshot con la fecha mas reciente disponible.
        Prefiere DB, con fallback a API.
        """
        df = self._query(
            "SELECT * FROM fondos_snapshot "
            "WHERE fecha = (SELECT MAX(fecha) FROM fondos_snapshot)"
        )
        if not df.empty:
            return df
        return self.snapshot_diario(force_api=True)

    # ───── series historicas ─────
    def serie_historica_fondo(self, fondo: str,
                              dias_lookback: int = 365) -> pd.DataFrame:
        """
        Serie de VCP de un fondo:
        primero busca en DB, completa con API los ultimos N dias si falta.
        """
        df = self._query(
            "SELECT fecha, vcp, patrimonio FROM fondos_snapshot "
            "WHERE fondo = ? ORDER BY fecha",
            (fondo,)
        )
        return df

    def completar_serie_api(self, fondo: str, tipo: str,
                             fechas: list[date]) -> int:
        """
        Para una lista de fechas, baja el snapshot de la API si no existe en DB
        y lo guarda. Usalo con cuidado, son muchas llamadas HTTP.
        """
        insertadas = 0
        for f in fechas:
            f_iso = f.isoformat()
            existe = self._query(
                "SELECT 1 FROM fondos_snapshot WHERE fecha=? AND fondo=? LIMIT 1",
                (f_iso, fondo)
            )
            if not existe.empty:
                continue
            df_dia = self.fetch_fecha_api(tipo, f)
            if df_dia.empty:
                continue
            self.guardar_snapshot(df_dia)
            insertadas += 1
        return insertadas

    # ───── inflacion ─────
    def inflacion(self) -> pd.DataFrame:
        """Devuelve inflacion mensual. Cachea en SQLite."""
        df = self._query("SELECT * FROM inflacion ORDER BY fecha")
        if df.empty or (pd.Timestamp.today().normalize() -
                        pd.to_datetime(df["fecha"].max())).days > 30:
            data = _api_get("/v1/finanzas/indices/inflacion")
            if data:
                df_api = pd.DataFrame(data)[["fecha", "valor"]]
                with self._conn() as c:
                    c.executemany(
                        "INSERT OR REPLACE INTO inflacion VALUES (?,?)",
                        df_api.itertuples(index=False, name=None)
                    )
                df = df_api.sort_values("fecha")
        return df

    def inflacion_acumulada(self, meses: int = 12) -> float:
        """Inflacion acumulada de los ultimos N meses, en %."""
        df = self.inflacion()
        if df.empty:
            return 0.0
        ultimos = df.tail(meses)
        acum = 1.0
        for _, row in ultimos.iterrows():
            acum *= (1 + row["valor"] / 100)
        return round((acum - 1) * 100, 2)

    # ───── dolar ─────
    def dolar(self, tipos=("oficial", "blue", "bolsa")) -> pd.DataFrame:
        """Cotizaciones dolar (compra/venta) para los tipos pedidos."""
        # Siempre refrescamos porque la API es barata
        dfs = []
        for t in tipos:
            data = _api_get(f"/v1/cotizaciones/dolares/{t}")
            if not data:
                continue
            df = pd.DataFrame(data)
            df["tipo"] = t
            dfs.append(df)
        if not dfs:
            return self._query("SELECT * FROM dolar")
        df_all = pd.concat(dfs, ignore_index=True)
        with self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO dolar VALUES (?,?,?,?)",
                df_all[["fecha", "tipo", "compra", "venta"]].itertuples(index=False, name=None)
            )
        return df_all

    # ───── utilidades ─────
    def _query(self, sql: str, params=()) -> pd.DataFrame:
        with self._conn() as c:
            return pd.read_sql_query(sql, c, params=params)

    def estado_db(self) -> dict:
        """Resumen rapido del estado de la DB."""
        r = {}
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT COUNT(*) FROM fondos_snapshot")
            r["filas_snapshots"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT fecha) FROM fondos_snapshot")
            r["dias_con_datos"] = cur.fetchone()[0]
            cur.execute("SELECT MIN(fecha), MAX(fecha) FROM fondos_snapshot")
            r["rango_fechas"] = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM inflacion")
            r["filas_inflacion"] = cur.fetchone()[0]
        return r


# ──────────────────────────────────────────────────────────────
# CLI rapido para verificar
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    dl = DataLayer()
    print(f"🗄️  DB: {dl.db_path}")
    print(f"📊 Estado inicial: {dl.estado_db()}")
    print("⏳ Bajando snapshot...")
    df = dl.snapshot_diario(force_api=True)
    print(f"   → {len(df)} fondos guardados")
    print(f"📊 Estado final:   {dl.estado_db()}")
    print(f"💰 Inflación 12m:  {dl.inflacion_acumulada()}%")
