# Predix: backend

API de **Predix**, el observatorio de InnovaLab sobre trabajo y formación en Argentina, Chile y
Uruguay (antes Observa Tendencias; el repositorio conserva ese nombre). FastAPI + PostgreSQL
(Supabase). La estructura sigue `backend_plan_ES.md`.

Las instrucciones completas de instalación y puesta en marcha están en
[`../README.md`](../README.md). La publicación en la nube, en [`../docs/despliegue.md`](../docs/despliegue.md).

Resumen (desde esta carpeta, con el entorno virtual activo):

```powershell
pip install -e ".[dev]"
copy .env.example .env           # completar DATABASE_URL y AUTH_SECRET (GOOGLE_CLIENT_ID es opcional)
docker compose up -d             # Postgres local
alembic upgrade head             # hasta 0032
python -m seeds.load
python -m app.jobs.create_user   # usuario para entrar a los frontends
uvicorn app.main:app --reload --port 8010    # http://localhost:8010/docs
pytest
```

`pytest` supone el ingreso con Google apagado: si tu `.env` tiene `GOOGLE_CLIENT_ID`, corré
`GOOGLE_CLIENT_ID= pytest` (la variable vacía tiene prioridad sobre `.env`).

## Cuentas y acceso

Los roles y sus permisos están en `config/app.yaml → auth.roles`.

| Cuenta | Cómo se crea | Qué ve |
|---|---|---|
| **Gratuita** (`free`) | Sola, la primera vez que alguien entra con **Continuar con Google** | Inicio y Panorama. Sin Pixi |
| **Acceso completo** | La crea un administrador (`python -m app.jobs.create_user` o *Usuarios y accesos*), o cambia el rol de una cuenta gratuita | Todo, según su rol |

- **Ingreso con Google:** `POST /api/v1/auth/google` recibe la credencial del botón de Google y
  la verifica con `google-auth`: el destinatario tiene que ser nuestro client ID, el emisor Google y
  el correo verificado. Busca al usuario por su id de Google o por su correo; si no existe, lo crea
  con el rol `auth.google.signup_role`, sin contraseña. Una cuenta creada con contraseña puede entrar
  también con Google si usa el mismo correo.
- **Configuración:** `GOOGLE_CLIENT_ID` en `.env` (backend) y el mismo valor en
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend). Vacío: no hay botón de Google y la ruta responde 503.
  El cliente OAuth es de tipo *Aplicación web*; sus orígenes autorizados son las direcciones del
  frontend: en local, `http://localhost` y el puerto que uses (`npm run dev` usa `http://localhost:3001`);
  en producción, la dirección de Vercel.
- **Qué se guarda:** nombre, correo e id de Google (columna `users.google_sub`, migración 0032).
  El frontend lo explica en `/privacidad`.
- **Qué se protege y dónde:** el asistente exige el permiso `view` (`GET /api/v1/assistant`
  devuelve `can_ask`). Las rutas de datos de solo lectura son públicas; las páginas fuera de Inicio y Panorama
  se ocultan en el frontend.

## Asistente: Pixi

Pixi (antes Baqueano) responde con los datos del observatorio. Las preguntas frecuentes se
contestan con plantillas (`assistant.scripted`, por frases exactas en `intent_words`); el resto, un
modelo que consulta los endpoints de lectura definidos en `assistant.tools`. Cada número de la
respuesta tiene que aparecer en los datos consultados: si no, la respuesta se bloquea.

Herramientas del Panorama: `indicadores_panorama` (los indicadores nacionales por dominio) y
`serie_indicador` (la serie observada de un indicador y país, con su descripción). La plantilla de
metodología responde solo preguntas sobre el ISE; las de otros indicadores van al modelo.

**Límite:** 25 preguntas por cuenta por día y 500 en total (`assistant.limits`). Cuentan solo las que
responde el modelo; las plantillas, las que fallan y las que se detienen, no. El día se cuenta en UTC.

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py              # punto de entrada FastAPI
│   ├── api/v1/              # routers: catálogo, indicadores, ISE, habilidades y brechas,
│   │                        #   alertas, fuentes, carga de archivos (datasets), usuarios y
│   │                        #   sesión, asistente, y los índices de cada módulo
│   ├── assistant/           # asistente (Pixi): plantillas de respuesta, herramientas (endpoints de
│   │                        #   lectura), búsqueda externa solo para los indicadores
│   │                        #   experimentales, proveedores de modelo, chequeo de números
│   ├── core/                # configuración (.env y YAML), base, sesión, búsqueda de texto,
│   │                        #   contraseñas, tokens e ingreso con Google (auth.py)
│   ├── models/              # modelos SQLAlchemy (catálogo, fuentes, cálculos, usuarios, asistente)
│   ├── schemas/             # esquemas de respuesta de la API
│   ├── connectors/          # conectores a fuentes externas
│   ├── datasets/            # archivos oficiales y carga manual: perfiles, control del archivo,
│   │                        #   lectura, validación y carga. También universidades, carreras por
│   │                        #   institución, CEP-XXI y el dólar oficial del BCRA
│   ├── ingestion/           # pipeline de actualización, historial de revisiones, CSV del equipo
│   ├── normalization/       # correspondencias, períodos, unidades
│   ├── analytics/           # tendencias, proyecciones, ISE, brechas, alertas, recálculo,
│   │                        #   titulados por sector, indicadores por sector y de género, e
│   │                        #   indicadores experimentales (Moctezuma, Ludita, Reina Roja, Sísifo)
│   ├── skills/              # ESCO: habilidades por ocupación y su jerarquía; versiones de
│   │                        #   ESCO y O*NET (Reina Roja)
│   ├── jobs/                # tareas de consola: run, recompute, scheduler, create_user…
│   ├── services/            # lógica compartida (observaciones, usuarios)
│   └── static/              # Explorer (herramienta de revisión)
├── config/                  # toda la configuración (YAML) y tablas de referencia
├── migrations/              # Alembic (hasta 0032: ingreso con Google)
├── seeds/                   # carga del catálogo, fuentes e indicadores desde config/
├── tests/                   # tests (base SQLite en memoria; no necesitan Postgres)
├── ml/occupation_match/     # prototipo: búsqueda de ocupaciones por significado
├── alembic.ini
├── pyproject.toml
├── .env.example
└── backend_plan_ES.md       # plan de arquitectura original
```
