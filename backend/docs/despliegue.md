# Despliegue: Supabase + Render + Vercel

Cómo publicar Observa Tendencias en la nube, con planes gratuitos.

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
| Código | Se sube a GitHub desde un clon aparte, con un PR a `main` |

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

En [render.com](https://render.com): **New → Web Service** → conectá el repositorio de GitHub.

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
| `CORS_ORIGINS` | `["https://<tu-proyecto>.vercel.app"]` (después del paso 3) |
| `ASSISTANT_PROVIDER` | `local`: el modelo abierto desde la API hospedada |
| `ASSISTANT_BASE_URL` | URL de la API del servicio elegido, compatible con OpenAI. Por ejemplo, Groq: `https://api.groq.com/openai/v1`; OpenRouter: `https://openrouter.ai/api/v1`; Together: `https://api.together.xyz/v1` |
| `ASSISTANT_MODEL` | Nombre del modelo en ese servicio. Tiene que aceptar herramientas ("tool calling" o "function calling"); elegirlo de su listado |
| `ASSISTANT_LOCAL_API_KEY` | La clave de ese servicio |

**Asistente en la nube:** ni Render ni Vercel pueden correr Ollama. El Baqueano usa el mismo tipo
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

En [vercel.com](https://vercel.com): **Add New → Project** → importá el repositorio de GitHub.

| Campo | Valor |
|---|---|
| Root Directory | `backend/frontend_minimal` |
| Framework Preset | Next.js |
| Variable `NEXT_PUBLIC_API_URL` | La URL de Render, por ejemplo `https://observa-tendencias-api.onrender.com` |

Después de publicar, copiá la URL de Vercel en `CORS_ORIGINS` de Render (paso 2) y reiniciá el
servicio.

## 4. Verificar

1. `https://<api>.onrender.com/health` responde `{"status": "ok"}`.
2. `https://<proyecto>.vercel.app` muestra el inicio de sesión; entrá con el usuario del paso 1.
3. Panorama, Sectores y Ocupaciones muestran datos.
4. La pestaña "Preguntale al Baqueano" responde "¿Cómo se calcula el ISE?".
5. En Carga de datos se baja la plantilla y el ejemplo con errores se rechaza.

## Quién hace qué

| Paso | Necesita |
|---|---|
| Reactivar Supabase | Hecho (2026-11-01) |
| Contraseña de la base | Tu cuenta de Supabase |
| Cargar la base en la nube (paso 1) | La contraseña; se corre desde la computadora |
| Subir el código a GitHub | Clon aparte + PR, y aprobar el PR |
| Crear el servicio en Render y el proyecto en Vercel | Tu cuenta en cada sitio, conectada a GitHub |
| Clave de la API hospedada del asistente | Tu cuenta en el servicio elegido (Groq, Together, OpenRouter…) |
