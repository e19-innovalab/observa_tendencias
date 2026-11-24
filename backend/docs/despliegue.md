# Despliegue: Supabase + Render + Vercel

Cómo publicar Predix (antes Observa Tendencias) en la nube, con planes gratuitos.

```
Navegador ──► Vercel (frontend minimal, Next.js) ──► Render (API FastAPI) ──► Supabase (PostgreSQL)
```

- **Vercel:** el frontend minimal. Se conecta solo a la API; nunca a la base.
- **Render:** la API. Es el mismo código que corre en local, en un servicio web Python.
- **Supabase:** la base de datos, proyecto **Rumbo** (`mfoiqrnmzbipjfsitnbi`, São Paulo). La
  conexión se explica en [`conexion_supabase.md`](conexion_supabase.md).

El backend no va en Vercel por cuatro razones:
- sus dependencias (pandas, statsmodels, scikit-learn) superan el tamaño máximo de una función;
- las cargas manuales se guardan en disco;
- los recálculos duran más que el tiempo máximo de una función;
- el modelo local del asistente no corre ahí.

## Decisiones tomadas (2026-11-01)

| Tema | Decisión |
|---|---|
| Base | Supabase, plan gratuito (500 MB). En la nube se **recalcula todo desde las fuentes**, no se copia la base local. El historial de la nube empieza ese día; el historial completo de antes queda en la base local |
| API | Render, plan gratuito |
| Frontend | Vercel, plan gratuito |
| Asistente en la nube | El mismo tipo de modelo abierto (familias Qwen o Llama), pero desde una **API hospedada** compatible con OpenAI (Groq, Together, OpenRouter…), porque ni Render ni Vercel pueden correr Ollama. En la computadora sigue Ollama |
| Código | Repo privado propio, [`paulajve/observa_tendencias`](https://github.com/paulajve/observa_tendencias) (rama `main`), con la misma estructura que el repo del equipo. Render y Vercel despliegan desde ahí, porque conectarlos al repo de la organización `e19-innovalab` requiere que un dueño de la organización autorice sus apps. El PR #28 al repo del equipo queda abierto |

## 1. Base de datos en Supabase

El proyecto Rumbo estaba pausado: el plan gratuito pausa los proyectos que no se usan durante 7
días. Se reactivó el 2026-11-01.

1. En Supabase, botón **Connect** → **Session pooler**: copiá la cadena de conexión. La contraseña
   se ve o se restablece en Project Settings → Database. No la guardes en el repositorio.
2. Desde `backend/backend` en tu computadora, con esa cadena (cambiá `postgresql://` por
   `postgresql+psycopg://`):

   ```bash
   export DATABASE_URL='postgresql+psycopg://postgres.mfoiqrnmzbipjfsitnbi:[CLAVE]@aws-1-sa-east-1.pooler.supabase.com:5432/postgres'
   # tablas: en una base vacía se crean desde los modelos y se marca la última migración
   # (la cadena de migraciones no corre desde cero: ver la nota de abajo)
   python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(engine)"
   alembic stamp head
   python -m seeds.load                 # catálogo, fuentes e indicadores
   python -m app.jobs.run --all         # descarga todas las fuentes y recalcula (puede tardar ~1 hora)
   python -m app.ingestion.load_analytics   # CSV del equipo de datos
   python -m app.jobs.create_user       # usuario administrador para entrar
   unset DATABASE_URL                   # volver a la base local
   ```

   La variable del entorno tiene prioridad sobre `.env`, así que tu `.env` local no cambia.

**Por qué no `alembic upgrade head` en una base vacía.** Las primeras migraciones crean las tablas
con la definición actual de los modelos, que ya incluye columnas agregadas después. Por eso una
migración posterior falla al intentar agregarlas de nuevo (por ejemplo, `relation` en
`occupation_skills`). Ninguna migración mueve datos, así que crear las tablas desde los modelos y
marcar la última migración (`stamp head`) deja la base igual que una migrada. Desde ahí,
`alembic upgrade head` aplica solo las migraciones nuevas. Se probó el 2026-11-01 sobre un Postgres
vacío: 46 tablas, migración `0025`, catálogo cargado.

**Orden:** primero este paso y después Render (paso 2). El comando de inicio de Render corre
`alembic upgrade head`, que sobre una base vacía fallaría.

**Límites del plan gratuito:**
- 500 MB de base. Una base recién calculada pesa unos 250–300 MB.
- Cada cambio de metodología de las brechas agrega una versión completa de unos 120 MB, porque el
  historial no se borra (`analytics.yaml → recompute.keep_superseded_results`). Con dos o tres
  cambios se llega al límite: en ese momento hay que pasar a Pro o decidir qué historial queda en
  la nube.
- El proyecto se pausa tras 7 días sin uso. Se reactiva desde el panel.

## 2. API en Render

En [render.com](https://render.com): **New → Web Service** → conectá el repositorio `paulajve/observa_tendencias`.

| Campo | Valor |
|---|---|
| Branch | `main` |
| Root Directory | `backend/backend` |
| Runtime | Python 3 |
| Build Command | `pip install .` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Instance Type | Free |

**Variables de entorno** (Environment):

| Variable | Valor |
|---|---|
| `PYTHON_VERSION` | `3.13.4` (la misma que en local) |
| `DATABASE_URL` | La cadena del Session pooler de Supabase (con `postgresql+psycopg://`) |
| `AUTH_SECRET` | Una clave nueva: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Distinta de la local |
| `ADMIN_API_KEY` | Una clave nueva, para scripts |
| `GOOGLE_CLIENT_ID` | El client ID de "Continuar con Google" (Google Cloud → Credenciales). No es secreto. Vacío: sin ingreso con Google |
| `CORS_ORIGINS` | `["https://<tu-proyecto>.vercel.app"]` (después del paso 3) |
| `ASSISTANT_PROVIDER` | `local`: el modelo abierto desde la API hospedada |
| `ASSISTANT_BASE_URL` | URL de la API del servicio elegido, compatible con OpenAI. Por ejemplo, Groq: `https://api.groq.com/openai/v1`; OpenRouter: `https://openrouter.ai/api/v1`; Together: `https://api.together.xyz/v1` |
| `ASSISTANT_MODEL` | Nombre del modelo en ese servicio. Tiene que aceptar herramientas ("tool calling" o "function calling"); elegirlo de su listado |
| `ASSISTANT_LOCAL_API_KEY` | La clave de ese servicio |

**Asistente en la nube:** ni Render ni Vercel pueden correr Ollama. Pixi usa el mismo tipo
de modelo abierto a través de una API hospedada: es más rápido (1–5 segundos) y, con nuestro volumen,
gratis o casi gratis. Antes de elegir el servicio, revisar sus condiciones actuales de uso
gratuito y de precios. Hay dos cosas para saber:
- las preguntas de los usuarios pasan por ese servicio; los datos son estadística pública, pero
  las preguntas salen de nuestros servidores;
- las preguntas frecuentes se siguen respondiendo por plantilla, sin modelo.

Sin estas variables, solo responden las plantillas. Con Claude, la alternativa es
`ASSISTANT_PROVIDER=anthropic` y `ANTHROPIC_API_KEY`.

**Límites del plan gratuito de Render:**
- **Se duerme tras 15 minutos sin uso.** La primera visita después tarda unos 30–60 segundos.
- **Tiene 512 MB de memoria.** Confirmar una carga manual recalcula todo dentro del pedido y podría
  quedarse sin memoria. Si pasa, conviene recalcular desde la computadora
  (`python -m app.jobs.recompute` con el `DATABASE_URL` de Supabase).
- **El disco se borra en cada despliegue.** Los archivos cargados a mano se pierden, aunque sus
  datos y su registro quedan en la base. Para conservarlos hace falta un disco de Render (pago) o
  guardarlos en Supabase Storage (requiere desarrollo).
- **No hay actualización automática.** El scheduler (`python -m app.jobs.scheduler`) necesita un
  proceso aparte o un Cron Job de Render, que son pagos. Mientras tanto, se actualiza a mano desde
  la computadora con `python -m app.jobs.run --all`.

## 3. Frontend en Vercel

En [vercel.com](https://vercel.com): **Add New → Project** → importá el repositorio `paulajve/observa_tendencias`.

| Campo | Valor |
|---|---|
| Root Directory | `backend/frontend_minimal` |
| Framework Preset | Next.js |
| Variable `NEXT_PUBLIC_API_URL` | La URL de Render, por ejemplo `https://observa-tendencias-api.onrender.com` |
| Variable `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | El mismo client ID que `GOOGLE_CLIENT_ID` de Render. Se lee al construir: después de cambiarlo, volver a desplegar |

Después de publicar, copiá la URL de Vercel en `CORS_ORIGINS` de Render (paso 2) y reiniciá el
servicio.

**Ingreso con Google:** en Google Cloud → Google Auth Platform → Clientes → *Predix web*, agregá la
URL de Vercel (por ejemplo `https://predix-silk.vercel.app`) a **Orígenes de JavaScript autorizados**.
Sin URI de redirección: el botón usa una ventana emergente. El cliente es el mismo que en local
(`http://localhost` y `http://localhost:3001`). La app tiene que estar publicada (*Audience →
Publicar app*) para que entre cualquier cuenta de Google. Sin logo no hace falta verificarla; con
logo, Google puede pedir una verificación que exige página de inicio y política de privacidad
públicas (`/privacidad`).

## 4. Verificar

1. `https://<api>.onrender.com/health` responde `{"status": "ok"}`.
2. `https://<proyecto>.vercel.app` muestra el inicio de sesión; entrá con el usuario del paso 1.
   Con `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, aparece **Continuar con Google**: una cuenta nueva entra como
   gratuita y ve solo Inicio y Panorama, sin Pixi.
3. Panorama, Sectores y Ocupaciones muestran datos.
4. Con acceso completo, la pestaña "Preguntale a Pixi" responde "¿Cómo se calcula el ISE?".
5. En Carga de datos se baja la plantilla y el ejemplo con errores se rechaza.

## 5. Después de publicar una versión con datos nuevos

Render corre `alembic upgrade head` al arrancar: **al unir el PR, las migraciones se aplican solas en producción.** Conviene hacer una copia de la base antes. Las tablas nuevas quedan vacías hasta cargarlas, en este orden, con `python -m app.jobs.run --source <fuente>`:

1. `universidades_egresados` y `carreras_seguimiento`: titulados por institución, sector y sexo. Recalculan las tendencias y los indicadores por sector y de género.
2. `bcra_dolar`: el dólar oficial diario.
3. `cep_xxi_argentina`: empleo y salarios de Argentina, que usan ese dólar. También carga los factores PPA.
4. `esco` o, sin tocar las habilidades, `run_esco_occupations`: las ocupaciones ESCO de cada grupo para los enlaces y el buscador.
5. Solo el ISE nuevo, con `recompute_employability`: sin él, Sectores y Ocupaciones quedan vacíos.

**En el plan gratuito, no correr `python -m app.jobs.recompute` ni la fuente `esco` completos.** Borran y vuelven a escribir las brechas (unos 199 MB) en una sola transacción, y la base puede pasar de 500 MB y quedar en solo lectura. Con el plan Pro sí se pueden correr; el recálculo completo también calcula las tendencias de los indicadores nuevos y puede generar alertas.

**Fuentes e indicadores nuevos:** hay que registrarlos antes de cargarlos, insertando solo los que falten. `python -m seeds.load` también borra las ocupaciones que ya no están en la configuración, junto con sus datos, así que conviene revisarlo antes de correrlo en producción.

**Caché de Vercel:** el frontend guarda las respuestas de la API hasta una hora (Sectores y Ocupaciones, 5 minutos). Después de una carga, esas pantallas pueden seguir vacías durante ese tiempo.

Las fuentes diarias y mensuales solo avanzan si hay un programador de tareas. Si no lo hay, hay que correrlas a mano.

## 6. Actualización de noviembre de 2026 (Predix)

Lo que hace falta para publicar Predix, Pixi, el ingreso con Google y los ocupados con educación
superior por sexo. Primero el código; los datos, después.

1. **Código:** PR al repositorio personal y unirlo. Render aplica la migración `0032` al arrancar
   (columna `users.google_sub`; la contraseña pasa a ser opcional).
2. **Variables:** `GOOGLE_CLIENT_ID` en Render y `NEXT_PUBLIC_GOOGLE_CLIENT_ID` en Vercel (volver a
   desplegar Vercel). Agregar la URL de Vercel a `CORS_ORIGINS` y a los orígenes del cliente de
   Google (paso 3).
3. **Datos**, desde la computadora y con el `DATABASE_URL` de Supabase. Sin `seeds.load` ni
   recálculo completo (sección 5):
   - registrar `employment_tertiary_women` y `employment_tertiary_men`, cargar solo esas dos series
     de ILOSTAT y calcular su tendencia;
   - `lower_secondary_completion`: actualizar el indicador (tasa bruta, sin tope de 100 %) y
     recalcular solo ese;
   - `unemployment_rate`: actualizar su descripción (Pixi la lee);
   - Moctezuma: actualizar el texto de su metodología (la nota de que el 0–100 es una posición en el
     grupo). Se actualiza al recalcular ese indicador; como en el plan gratuito no se recalcula todo,
     hay que actualizarla aparte.
4. **Caché de Vercel:** purgarla, o esperar una hora.
5. **Verificar:** pasos 2 y 4 de la sección 4, la tercera sección de Género y, en Panorama, la proyección
   de la finalización de la secundaria baja de Chile por encima de 100 %.

## Quién hace qué

| Paso | Necesita |
|---|---|
| Reactivar Supabase | Hecho (2026-11-01) |
| Contraseña de la base | Tu cuenta de Supabase |
| Cargar la base en la nube (paso 1) | La contraseña; se corre desde la computadora |
| Subir el código a GitHub | Clon aparte + PR, y aprobar el PR |
| Crear el servicio en Render y el proyecto en Vercel | Tu cuenta en cada sitio, conectada a GitHub |
| Clave de la API hospedada del asistente | Tu cuenta en el servicio elegido (Groq, Together, OpenRouter…) |
| Cliente OAuth de Google | Tu cuenta de Google Cloud (proyecto con el cliente *Predix web*) |
