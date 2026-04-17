# Oportunidades — Proyecto FCI Argentina

Análisis estratégico: dónde puede este proyecto convertirse en algo vendible, diferenciable y alineado con tu perfil (FIUBA + EY Technology Risk).

---

## 1. Mapa del ecosistema actual

### Plataformas broker-céntricas (push product)
Cada broker muestra los fondos que administra o distribuye. El conflicto de interés es estructural: no van a decirte que el fondo de la competencia es mejor que el propio.

- **Cocos Capital** — app mobile-first, muy buena UX, fuerte en money market y "parking de pesos". Fondos propios Cocos.
- **Balanz** — oferta más amplia del mercado, incluye fondos Balanz + otras gestoras, research in-house.
- **IOL (Invertir Online)** — el clásico, oferta robusta, muchos bonos/letras en secundario.
- **Portfolio Personal, Allaria, Bull Market** — más tradicionales, perfil de ticket alto.

### Plataformas de datos / comparadores independientes
Acá está la competencia real porque son neutrales (o intentan serlo):

- **CAFCI oficial** — [comparador por nombre](https://www.cafci.org.ar/comparadorNombre.html). Datos crudos, UI de 2012, sin analítica.
- **EquityLens** — [fci-hoy](https://equitylens.com.ar/fci-hoy). **Competidor más parecido a lo que estás haciendo.** Ranking + comparador + datos descargables. Gratis.
- **fci.ar / Tablero FCI** — dashboard público, comparador básico.
- **Rankia Argentina** — blog + rankings de terceros.
- **cuajoa/FCI.ar en GitHub** — bot open source que publica rankings diarios en Twitter. Mismo gap técnico que vos: también usa ArgentinaDatos.

### Plataformas de contenido / research pago
- **Inversor Global** (Bull Market Group), **Hoja de Rutas** (Gustavo Neffa), **PPI Research** — newsletters con ideas de inversión. Rara vez muestran scorecards cuantitativos de fondos.

---

## 2. Gaps reales del mercado

Esto es lo que no hace nadie bien hoy (validado con una recorrida rápida). Tu ventaja está en atacar alguno.

### Gap 1 — Rendimiento **real** (inflation-adjusted) como métrica primaria
Casi todos publican rendimiento nominal. En un país con 30%+ de inflación, eso es un dato engañoso. El dato útil es cuánto preservás o ganás poder adquisitivo.  
**Tu dashboard ya lo calcula con fórmula de Fisher.** Posicionar esto como "primera métrica que vas a ver, no letra chica" es un diferenciador claro.

### Gap 2 — Análisis por administradora, no por fondo
La industria habla de "fondos" (cada clase como unidad). Pero la decisión de un inversor retail es: ¿confío en X gestora? Pocas plataformas agregan por administradora + muestran:
- cuántos de sus fondos le ganan sistemáticamente a la inflación,
- dispersión entre sus fondos (si todos se parecen o hay clases malísimas),
- tendencia de AUM (les entra o les sale plata).

**Tu tab "Administradoras" ya ataca esto.** Es contenido que vende en redes.

### Gap 3 — Riesgo operacional / gobierno corporativo del fund manager
Acá es donde tu **rol en EY Tech Risk es un superpoder**. Nadie en el mundo retail argentino analiza:
- ¿La administradora tiene antecedentes de errores de pricing del VCP?
- ¿Cambios bruscos de PM (portfolio manager)? *(dato público en resoluciones CNV)*
- ¿Segregación de custodia vs administración correcta?
- ¿Historial ante CNV: sanciones, advertencias, observaciones?

Un "rating de riesgo operativo" estilo Morningstar Analyst Rating pero con sabor Tech Risk. Nadie lo hace en Argentina. Le ganaría credibilidad enorme a un CV para consultoría financiera, asset management o fintech.

### Gap 4 — Tax reporting / régimen impositivo FCI
Para el retail: ¿cuánto pagás de ganancias por ese FCI? ¿Te conviene un FCI "ley 27.743" vs clase común? ¿Cómo impacta en Bienes Personales? La AFIP/ARCA no te ayuda, los brokers tampoco. Hay demanda real, pero requiere socio contable.

### Gap 5 — Alertas inteligentes personalizadas
"Tu fondo X perdió el tercer cuartil del ranking esta semana." Telegram bot + webhook. Bajo esfuerzo técnico, alto valor percibido. Se monetiza con freemium.

### Gap 6 — API limpia con métricas computadas
ArgentinaDatos y CAFCI dan datos crudos. Nadie ofrece un endpoint tipo `GET /fondos/:id/metrics` con RiskScore, sharpe, sortino, vs benchmark computado. Desarrolladores de fintech compran esto. B2B.

---

## 3. Ideas de producto, priorizadas

Ranking por **factibilidad × alineación con tu perfil**, no solamente por potencial.

### 🟢 A. Dashboard público + contenido en redes
**Qué**: Deployar el dashboard en Render/Railway en fcidata.com.ar (o nombre parecido). Twitter/X thread semanal con "el gráfico de la semana".  
**Por qué empezar por acá**: Cero costo fijo, construye audiencia, valida interés, prueba el posicionamiento de "rendimiento real > nominal".  
**Monetización eventual**: sponsored posts, enlaces afiliados a brokers, newsletter paga con más profundidad.  
**Esfuerzo**: bajo. Ya tenés el 70%.  
**Alineación con perfil**: media-alta. Buen portfolio piece para cualquier empresa financiera/fintech.

### 🟢 B. Scorecard de Riesgo Operacional (Tech Risk angle) — como newsletter + PDF mensual
**Qué**: Un documento mensual, tipo "Moody's de FCI argentinos", que rankee administradoras por score compuesto que incluya ops risk + performance real. Publicar en LinkedIn + newsletter.  
**Por qué**: Es LA cosa que nadie hace + es EXACTAMENTE lo que tu rol en EY te permite hacer con credibilidad.  
**Monetización**: freemium (ranking gratis, análisis detallado pago, $5-10/mes). O vender a asesores financieros independientes ($30-80/mes).  
**Esfuerzo**: medio. Requiere research de resoluciones CNV y una metodología bien documentada.  
**Alineación con perfil**: **máxima**. Es la combinación única FIUBA + EY que nadie más puede ofrecer sin contratar dos personas.

### 🟡 C. Alertas / bot de Telegram premium
**Qué**: Usuario ingresa sus fondos, recibe alertas cuando se degradan o hay mejor alternativa en su segmento.  
**Por qué**: demanda clara, bajo costo operativo.  
**Esfuerzo**: medio. Hosting con crons + Telegram API.  
**Alineación con perfil**: media. No explota tu ventaja Tech Risk.  
**Viralidad**: alta en Twitter-finanzas.

### 🟡 D. API B2B con métricas computadas
**Qué**: `api.fcidata.ar/v1/funds/rank`, `api.fcidata.ar/v1/funds/:fondo/scorecard`. Auth por API key, free tier + paga.  
**Por qué**: defensible, moat técnico.  
**Esfuerzo**: alto. Requiere infra seria, contratos, soporte.  
**Alineación con perfil**: alta técnicamente, pero B2B requiere ventas y eso lleva tiempo.  
**Timing**: no ahora. Dejarlo para después de validar A+B.

### 🟠 E. Tax reporting FCI
**Qué**: calculadora + generador de papeles para Ganancias/Bienes Personales.  
**Por qué**: dolor real, paga gente.  
**Contra**: regulación cambia, requiere socio contable, responsabilidad.  
**Alineación con perfil**: media. Lateral a vos.  
**Conclusión**: descartar por ahora.

---

## 4. Tu edge competitivo (leé esto antes de decidir)

Sos el único proyecto de este tipo hecho por alguien que:
1. **Es ingeniero informático de FIUBA** → podés construir el producto completo vos mismo, sin bloqueantes técnicos, y es señal de calidad para inversores/compradores.
2. **Trabaja en EY Technology Risk** → podés emitir opinión creíble sobre controles, gobierno y riesgo operacional. Ningún youtuber financiero puede.
3. **Está en último año de carrera** → tenés la ventana perfecta para meterle 6-12 meses fuerte sin la mochila de un full-time con hijos.

La combinación #1 + #2 es **muy rara** en el mercado argentino. Casi todos los creators de finanzas son contadores o economistas que contratan a un dev, o devs que no entienden finanzas. Vos estás en la intersección.

---

## 5. Plan de 90 días sugerido

### Semana 1-2 (mientras terminás funcionalidades del dashboard)
- Correr el snapshot diario y dejar acumular data
- Escribir un README decente en GitHub con la historia del hallazgo (29% le gana a inflación)
- Sacar un primer hilo en Twitter/X con los 3-4 gráficos más potentes

### Semana 3-6
- Deploy en Render/Railway con dominio propio
- Landing page simple con email capture ("newsletter mensual con el ranking")
- Análisis profundo de 1 administradora por semana (LinkedIn post + Twitter thread)

### Semana 7-12
- Primer PDF "Radar FCI Argentina — Edición X". Exportable desde el dashboard.
- Pricing del premium tier si hay >200 suscriptores al newsletter
- Conversación con 5 asesores financieros independientes para validar pricing B2B

### Métricas de éxito de 90 días
- 500+ suscriptores al newsletter
- 3000+ visitas al dashboard en total
- 10+ interacciones con asesores (LinkedIn DMs valen)
- 1 menção en medio financiero argentino (iProfesional, Cronista, Ámbito)

---

## 6. Aspectos específicos de tu perfil que te conviene explotar

### Para tu CV / LinkedIn
- Este proyecto es **portfolio piece** de altísimo valor. Mostralo en LinkedIn con los gráficos, no sólo código.
- Menciones útiles: "Built and deployed production dashboard analyzing X funds, applied Tech Risk frameworks to evaluate fund manager operational risk".

### Para relaciones en EY
- Internamente en EY, **Financial Services Advisory** y **FSRisk** son las áreas donde este dominio te puede servir. Cuando venga la conversación de ascenso o rotación, tener un proyecto público sobre FCI es enorme.
- Cuidar: el proyecto no debe usar información no pública de EY ni de clientes; no debe parecer que competís con consultoría EY. Publicá a título personal, con disclaimer.

### Para tu tesis / proyecto final FIUBA
- ¿Podés transformar esto en el proyecto final? "Sistema de análisis cuantitativo de FCI con framework de riesgo operacional". Tutor candidato: alguien de FIUBA que dé Finanzas o Data Science. Si sale bien, tenés TPI + proyecto comercial en paralelo.

### Para contactos que te conviene hacer ahora
- **Gonzalo Martínez Mosquera** (Cocos Capital, founder)
- **Marcos Galperín-adjacent people** (Mercado Pago tiene productos financieros)
- **Marina Dal Poggetto** (Eco Go) — voz con alcance, puede amplificar
- **People from CAFCI** — si vas a trabajar sobre sus datos, tenerlos como "conocidos" te dá opcionalidad (colaboración oficial, licenciamiento, etc.).

---

## 7. Decisiones que te conviene tomar en las próximas 2 semanas

1. **¿Alias público del proyecto?** Pensá un nombre: "FCIradar", "Radar FCI", "EquityWatch AR", "CuotaParte". Comprá el dominio .com.ar antes de publicar nada.
2. **¿Licencia?** MIT / Apache 2.0 en el código pero datos y metodología pueden quedar cerrados. Es lo que hace Morningstar.
3. **¿Twitter aparte o tu cuenta personal?** Aparte es mejor para foco, personal es mejor para construir marca propia junto al proyecto.
4. **¿Render vs Railway vs Vercel (solo front)?** Para Dash → Render free tier ajustado. Railway pago arranca barato. Si vas por uptime serio, Fly.io es alternativa.

---

## 8. Riesgos a tener en el radar

- **Compliance CNV**: si emitís "recomendaciones de inversión" sin ser agente registrado, es infracción. Hay que usar language tipo "información educativa, no constituye asesoramiento financiero".
- **Calidad de datos**: ArgentinaDatos es un scraper de CAFCI. Si CAFCI cambia schema o bloquea, te quedás sin fuente. Mitigación: ir bajando directo de CAFCI/CNV en paralelo.
- **Conflicto de interés EY**: cuidar con Clientes EY que sean administradoras. Revisar política interna de side-projects antes de monetizar.

---

## Dónde empezar el lunes

Abrí una issue en GitHub que diga "Semana 1: deploy + primer thread". Elegí 1 idea de la sección 3 como foco principal y dejá las otras como notas. **La trampa más grande en este punto es diluir esfuerzo en las 5 ideas. Elegí 1 y ejecutala 8 semanas, después decidís.**

Mi recomendación: **idea A (dashboard público + contenido) como foco, y empezar a construir la idea B (scorecard operacional) como subproducto de contenido** (un thread mensual alcanza). Cuando la B gane tracción, te cambiás de eje.
