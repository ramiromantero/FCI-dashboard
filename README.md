# FCI Argentina — Dashboard y análisis

Dashboard interactivo de Fondos Comunes de Inversión (FCI) argentinos con análisis de rendimiento nominal y real, ranking por administradora, comparador histórico y scorecard de riesgo.

**Hallazgo principal:** durante los últimos 12 meses (abr-2025 a abr-2026), solo el **29%** de los fondos de renta fija le ganaron a una inflación acumulada del **32,64%**. La mediana de rendimiento fue **9,15%**, lo que implica pérdida de poder adquisitivo para la mayoría de inversores retail.

---

## Stack

- **Python 3.11** + Pandas + Requests
- **Dash 3.x** + Dash Bootstrap Components (tema DARKLY) + Dash AG Grid
- **Plotly** para visualizaciones
- **SQLite** para cache local y acumulación histórica

---

## Cómo correr

```bash
# 1. Activar entorno conda
conda activate dash-panel

# 2. Instalar dependencias
pip install dash dash-bootstrap-components dash-ag-grid plotly requests pandas numpy

# 3. Inicializar base y descargar snapshot
python snapshot_diario.py

# 4. Levantar dashboard
cd dashboard
python dashboard_fci.py
```

Abrir en el navegador: <http://localhost:8050>

### Schedular snapshot diario (Windows Task Scheduler)

```
Programa:   C:\Users\<usuario>\anaconda3\envs\dash-panel\python.exe
Argumentos: C:\Users\<usuario>\Documents\Proyectos\snapshot_diario.py
Frecuencia: diaria, 20:00 (post cierre de mercado)
```

---

## Estructura del proyecto

```
Proyectos/
├── data_layer.py          Capa única de acceso a datos (API + SQLite)
├── analisis.py            Funciones de análisis puro (rendimientos, scorecard)
├── snapshot_diario.py     Script standalone schedulable
├── explorar_cafci.py      Exploración inicial (legado)
├── fci.db                 SQLite con snapshots acumulados
├── OPORTUNIDADES.md       Análisis estratégico de mercado y producto
├── dashboard/
│   ├── dashboard_fci.py   App Dash con 5 tabs
│   └── assets/custom.css
└── README.md
```

---

## Tabs del dashboard

1. **Resumen** — KPIs globales y distribución de rendimientos de renta fija.
2. **Por Tipo** — comparación entre renta fija, variable, mercado de dinero y mixta.
3. **Administradoras** — ranking de managers del mercado argentino con rendimiento mediano y % de fondos que ganaron a la inflación.
4. **Comparador** — elige hasta 4 fondos y compará su evolución VCP en base 100.
5. **Scorecard** — RiskScore por fondo con ponderación estilo Tech Risk (performance, consistencia, tamaño, concentración).

---

## Fuentes de datos

| Fuente | Qué aporta | Link |
|---|---|---|
| ArgentinaDatos API | Endpoints `/fci/*`, `/indices/inflacion`, `/cotizaciones/dolares/*`. No requiere auth. | <https://api.argentinadatos.com> |
| CAFCI | Cámara Argentina de FCI — emisor original de los datos diarios que consume ArgentinaDatos. | <https://www.cafci.org.ar/> |
| CNV | Comisión Nacional de Valores — regulador. Resoluciones, sanciones, registro de administradoras. | <https://www.cnv.gov.ar/sitioWeb/FondosComunesInversion> |
| INDEC | Índice de precios al consumidor mensual. | <https://www.indec.gob.ar/indec/web/Nivel3-Tema-3-5> |

### Endpoints relevantes de ArgentinaDatos

| Endpoint | Devuelve |
|---|---|
| `/v1/finanzas/fci/rentaFija/ultimo` | Fondos de renta fija del último día |
| `/v1/finanzas/fci/rentaVariable/ultimo` | Fondos de renta variable |
| `/v1/finanzas/fci/mercadoDinero/ultimo` | Fondos mercado de dinero |
| `/v1/finanzas/fci/rentaMixta/ultimo` | Fondos renta mixta |
| `/v1/finanzas/fci/rentaFija/YYYY/MM/DD` | Datos de una fecha específica |
| `/v1/finanzas/indices/inflacion` | Inflación mensual histórica |
| `/v1/cotizaciones/dolares/{tipo}` | Cotizaciones dólar oficial / blue / bolsa |

Importante sobre fechas: la API tiene un día de delay, formato `YYYY/MM/DD` con barras, y no todos los días tienen datos (solo hábiles). Usar `ultimo` para obtener el último día disponible.

---

## Metodología

### Rendimiento nominal
```
rendimiento_% = (VCP_fin / VCP_inicio − 1) × 100
```
Punta a punta, calculado sobre días hábiles bursátiles.

### Rendimiento real (fórmula de Fisher)
```
rendimiento_real = ((1 + nominal) / (1 + inflación) − 1) × 100
```
Deflacta el nominal con la inflación acumulada del período. Es la métrica correcta para medir preservación de poder adquisitivo.

### RiskScore (0-100)
Promedio ponderado de 4 dimensiones inspiradas en frameworks de auditoría IT:

| Componente | Peso | Descripción |
|---|---|---|
| Performance real | 45% | `50 + rendimiento_real × 2.5`, clipped a [0, 100] |
| Consistencia | 25% | Flag binario: ¿le ganó a la inflación? |
| Tamaño (AUM) | 20% | `log10(patrimonio)` normalizado: 100M → 0, 100.000M → 100 |
| Concentración | 10% | Penaliza fondos que concentran >5% del segmento |

Semáforo: 🟢 ≥70 · 🟡 50-70 · 🔴 <50

### Filtros de datos
Se excluyen del análisis:
- Filas agregadas de CAFCI sin `vcp` ni `fecha` reales (categorías, benchmarks).
- Fondos con patrimonio NaN o < 1M pesos (caparazones sin inversores).
- Fondos con VCP de inicio exactamente redondo en múltiplos de 1000 (valor nominal contable).
- Outliers de rendimiento fuera del rango [−50%, +200%] (casos puntuales a analizar aparte).

---

## Descargo (disclaimer)

**Este proyecto tiene fines exclusivamente educativos e informativos.** No constituye asesoramiento financiero, recomendación de inversión, ni oferta pública de títulos valores. La inversión en FCI conlleva riesgos; los rendimientos pasados no garantizan resultados futuros. Las decisiones de inversión son responsabilidad exclusiva del usuario, quien debe consultar con un Agente de Colocación y Distribución Integral de FCI matriculado en la CNV.

Proyecto independiente. No afiliado a CAFCI, CNV, ni ninguna administradora de fondos.

---

## Roadmap

- [x] Análisis de renta fija vs inflación
- [x] Dashboard interactivo con 5 tabs
- [x] Capa SQLite para cache y acumulación
- [x] Scorecard de riesgo
- [ ] Deploy público (Render/Railway)
- [ ] Landing con captura de emails
- [ ] Export a PDF del reporte mensual
- [ ] Bot de Telegram con alertas
- [ ] API pública con métricas computadas

Ver [OPORTUNIDADES.md](./OPORTUNIDADES.md) para el análisis estratégico completo.

---

## Licencia

MIT sobre el código. Los datos de CAFCI/CNV pertenecen a sus respectivos emisores.
