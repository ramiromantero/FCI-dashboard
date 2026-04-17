# Deploy a producción — FCI Dashboard

Guía paso a paso para dejar el dashboard corriendo en internet, gratis.

**Plataforma recomendada:** [Render](https://render.com/) free tier. Alternativa válida: Railway (~$5 de crédito inicial), Fly.io (más técnica, mejor volúmenes persistentes).

---

## Archivos ya incluidos en el repo

| Archivo | Para qué sirve |
|---|---|
| `app.py` | Entry point de producción. Importa la app Dash y expone `server` para gunicorn. |
| `requirements.txt` | Dependencias con versiones lockeadas (incluye gunicorn). |
| `Procfile` | Comando que arranca el servidor en Heroku/Railway/Render. |
| `render.yaml` | Blueprint de Render (infra as code). Deploy con 1 click. |
| `runtime.txt` | Le dice a Render qué versión de Python usar. |
| `.gitignore` | Excluye `.db`, `.csv`, logs y secretos. |

---

## Paso 1 — Verificar que todo funciona localmente en modo prod

Antes de tirar a producción, simular el entorno prod local:

```bash
# Activar tu env
conda activate dash-panel

# Instalar desde requirements.txt
pip install -r requirements.txt

# Correr como lo haría Render
PORT=8050 gunicorn app:server --workers 2 --threads 4 --timeout 180
```

Abrir `http://localhost:8050` y chequear que los 5 tabs cargan igual que en dev.

Si algo rompe acá, rompe en producción también. Corregí antes de seguir.

---

## Paso 2 — Ajuste cosmético manual en `dashboard/dashboard_fci.py`

Buscá en el footer esta línea (aprox línea 730-750):

```python
link_ext("Código en GitHub", "https://github.com/"),
```

Reemplazala por:

```python
link_ext("Código en GitHub", "https://github.com/ramiromantero/FCI-dashboard"),
```

Es un 1-liner, en el bloque `footer = html.Div([...])`.

---

## Paso 3 — Commit y push

```bash
cd C:\Users\Ramir\Documents\Proyectos\FCI-dashboard

git add app.py requirements.txt Procfile render.yaml runtime.txt .gitignore DEPLOY.md
git add dashboard/dashboard_fci.py   # si hiciste el ajuste del paso 2
git commit -m "feat: production deployment setup (Render/Railway)"
git push origin main
```

---

## Paso 4 — Deploy en Render

### Opción A — Blueprint (recomendada, 1 click)

1. Entrar a [dashboard.render.com](https://dashboard.render.com/)
2. Login con GitHub, autorizar acceso a `FCI-dashboard`
3. **New** → **Blueprint**
4. Seleccionar el repo `ramiromantero/FCI-dashboard`
5. Render lee `render.yaml` y crea el servicio automáticamente
6. Esperar ~3 min al primer build. Vas a ver el log en vivo.
7. Cuando termine, te da una URL tipo `https://fci-dashboard-xxxx.onrender.com`

### Opción B — Manual (si preferís control fino)

1. **New** → **Web Service**
2. Conectar el repo
3. Configurar:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:server --workers 2 --threads 4 --timeout 180 --bind 0.0.0.0:$PORT`
   - **Instance Type:** Free
4. Deploy.

---

## Paso 5 — Primer request

El free tier de Render **duerme** el servicio después de 15 min sin tráfico. El primer request después de eso tarda **~15-30 segundos** (cold start). Es normal.

Si vas a mandar el link a gente, hacé primero un request vos para "despertarlo" y que cuando lo abran responda rápido.

Upgrade a plan **Starter ($7/mes)** si querés que nunca se duerma.

---

## Consideraciones de datos en Render free

### Filesystem efímero
Cada vez que Render redeploya o el servicio se despierta desde sleep, `fci.db` se resetea. El `DataLayer` ya maneja esto: al bootear detecta que la DB está vacía y baja un snapshot fresco desde la API.

**Consecuencia práctica:** en prod no vas a acumular histórico local. Para series temporales reales tenés 3 opciones:

1. **Render Persistent Disk** (~$1/mes por 1GB) — agregar en `render.yaml`:
   ```yaml
   disk:
     name: fci-data
     mountPath: /opt/render/project/src/data
     sizeGB: 1
   ```
   Y cambiar `DB_PATH` en `data_layer.py` a `/opt/render/project/src/data/fci.db`.

2. **Render Cron Job + PostgreSQL free tier** — correr `snapshot_diario.py` diario contra un Postgres managed (Render tiene free tier de 90 días para DB).

3. **Seguir con SQLite efímero** y mantener el `snapshot_diario.py` corriendo en tu máquina con Task Scheduler como ya lo tenés. La web solo muestra el snapshot del día.

Para MVP, la opción 3 es suficiente.

---

## Paso 6 — Dominio custom (opcional, lindo)

Si compraste `fcidata.com.ar` o similar en Nic.ar:

1. En Render, sección **Settings → Custom Domain** → agregar tu dominio.
2. Render te da un CNAME tipo `something.onrender.com`.
3. En Nic.ar panel DNS → agregar registro CNAME apuntando a eso.
4. Esperar propagación (15 min a 24h).

SSL/HTTPS lo gestiona Render automáticamente vía Let's Encrypt.

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| Build falla en `pip install` | Versión Python incompatible | Verificá `runtime.txt` = `python-3.11.9` |
| `ModuleNotFoundError: dashboard` | `app.py` no encuentra el paquete | Asegurate que `dashboard/__init__.py` exista (podés crear vacío) |
| Página blanca en prod | Gunicorn timeout al cargar datos | Aumentar `--timeout` a 300 o bajar snapshot async |
| App tarda 30s en cargar | Cold start del free tier | Normal. Upgrade a starter o usar [cron-job.org](https://cron-job.org) para hacer ping cada 10 min |
| Error 502 Bad Gateway | Worker crasheó | Ver logs en Render → común: falla la API externa y no hay fallback |

---

## Monitoreo básico

1. **Render logs** — en el panel de Render, tab Logs. Persiste 1 día en free tier.
2. **Uptime** — [UptimeRobot](https://uptimerobot.com/) gratis te monitorea el endpoint cada 5 min.
3. **Analytics** — meter [Plausible](https://plausible.io/) (~$9/mes) o GA4 (gratis) para ver tráfico real.

---

## Dónde sumar después

Cuando esté todo estable, estos son los próximos ítems del roadmap según `OPORTUNIDADES.md`:

- [ ] Export a PDF mensual (ReportLab) → lead magnet
- [ ] Landing con captura de emails (Mailchimp / ConvertKit / Resend)
- [ ] Bot de Telegram con alertas
- [ ] API pública con métricas computadas (FastAPI)
