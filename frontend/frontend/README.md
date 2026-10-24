# Observa Tendencias – Frontend

Observatorio de datos de Argentina, Uruguay y Chile (Innova Lab). Este módulo es la
aplicación web que consume la API del backend (FastAPI + PostgreSQL) y muestra
indicadores, tendencias, proyecciones, ocupaciones y formación.

**Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Recharts · Zod ·
TanStack Query y nuqs (instalados, aún sin usar) · lucide-react · Supabase Auth.

Documentación relacionada: [`docs/api-contract.md`](../docs/api-contract.md) (endpoints y
qué pantalla usa cada uno) y el esquema de datos en `src/lib/schemas/api.ts`.

---

## 1. Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Node.js | 20.9 o superior (`node -v`) | Frontend |
| npm | viene con Node | Frontend |
| Git | cualquiera reciente | Repositorio |
| Python | ver `requires-python` en `backend/backend/pyproject.toml` | Backend |
| Docker Desktop | reciente | Base de datos del backend |

En Windows, Docker Desktop necesita WSL 2. Si el instalador lo pide, abrí PowerShell
**como administrador**, corré `wsl --install` y reiniciá.

---

## 2. Instalación solo del frontend

```bash
git clone <url-del-repo>
cd observa_tendencias
git checkout <tu-rama>          # por ejemplo frontend-main
cd frontend/frontend
npm install
```

Creá el archivo de variables de entorno a partir del ejemplo:

```bash
# macOS / Linux
cp .env.example .env.local

# Windows (PowerShell)
copy .env.example .env.local
```

Levantá el servidor de desarrollo:

```bash
npm run dev
```

Abrí <http://localhost:3000>. Sin el backend levantado, la pantalla se ve con datos
de ejemplo.

El acceso al observatorio es público y no requiere iniciar sesión. La pantalla opcional de
login/registro está en <http://localhost:3000/auth>; después de iniciar sesión, vuelve al
observatorio en <http://localhost:3000>.

---

## 3. Instalación del proyecto completo (backend + frontend)

El backend vive en `backend/backend/` y usa el puerto **8010**. Estos pasos son los del
README del equipo de backend.

### Backend

**Windows (PowerShell)**

```powershell
cd backend\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env          # cambiá la clave de Postgres y ADMIN_API_KEY
docker compose up -d            # Docker Desktop tiene que estar abierto
alembic upgrade head
python -m seeds.load
python -m app.jobs.run --all    # descarga datos de las fuentes: puede tardar varios minutos
python -m app.ingestion.load_analytics
uvicorn app.main:app --reload --port 8010
```

**macOS / Linux**

```bash
cd backend/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d
alembic upgrade head
python -m seeds.load
python -m app.jobs.run --all
python -m app.ingestion.load_analytics
uvicorn app.main:app --reload --port 8010
```

Verificá que funciona abriendo <http://localhost:8010/docs> (Swagger con todos los endpoints).

Después de reiniciar la computadora: abrí Docker Desktop, corré `docker compose up -d`,
activá el entorno virtual y volvé a levantar `uvicorn`. No hace falta repetir
`alembic` ni los seeds.

Errores frecuentes:

- `alembic` no se reconoce: el entorno virtual no está activo. Activalo de nuevo.
- Scripts bloqueados en PowerShell: corré una vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- El backend nunca se sube con su `.env`: contiene claves.

### Frontend

En otra terminal, desde `frontend/frontend/`, seguí los pasos de la sección 2. Con el backend
corriendo, el front puede apuntar a <http://localhost:8010>.

---

## 4. Variables de entorno

Archivo `frontend/frontend/.env.local` (no se sube a git; el modelo es
`frontend/frontend/.env.example`).

| Variable | Valor de ejemplo | Descripción |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8010` | URL base del backend |
| `NEXT_PUBLIC_SUPABASE_URL` | (URL del proyecto) | URL pública del proyecto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (clave pública/anon) | Clave pública para Supabase Auth |
| `NEXT_PUBLIC_USE_MOCKS` | `true` | Reservada para la capa de servicios: alterna datos de ejemplo y API real |
| `ADMIN_API_KEY` | (la del `.env` del backend) | Solo servidor. **Nunca** con prefijo `NEXT_PUBLIC_` |

Los endpoints de escritura del backend (marcar alertas, subir datasets, refrescar fuentes)
exigen el header `x-api-key`. Esa clave no puede estar en el navegador: esas llamadas
tienen que pasar por Route Handlers de Next.js (`src/app/api/...`).

Para login, registro y Google OAuth, completá las dos variables de Supabase. En Supabase
Auth, configurá `http://localhost:3000/auth/callback` como URL permitida de retorno. En el
`.env` del backend, `SUPABASE_REDIRECT_URL` debe apuntar a esa misma URL.

---

## 5. Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo en `localhost:3000` |
| `npm run build` | Compila para producción (detecta errores de tipos) |
| `npm run start` | Sirve la versión compilada |
| `npm run lint` | Revisa el código con ESLint |

Antes de abrir un PR, corré `npm run lint` y `npm run build`.

---

## 6. Estructura del código

```
frontend/frontend/src/
├─ app/                     # rutas (App Router). Cada carpeta es una URL
├─ components/ui/
│  ├─ layout/               # AppHeader, MainNav, PageHero
│  ├─ navigation/           # SectionTabs
│  ├─ filters/              # FilterBar
│  ├─ indicators/           # KpiCard, IndicatorSidebar
│  └─ charts/               # ChartCard, TrendLineChart, chartTheme
└─ lib/
   ├─ schemas/api.ts        # esquemas Zod de las respuestas del backend
   └─ utils/                # funciones auxiliares
```

Estructura objetivo a medida que crezca (cada tema autocontenido):

```
src/features/<tema>/        # ocupaciones, formacion, tendencias, ...
├─ components/
├─ hooks/
└─ api.ts                   # funciones que llaman a la API y validan con Zod
src/lib/api/                # cliente HTTP compartido
src/mocks/                  # respuestas reales del backend guardadas como JSON
```

Reglas del código:

- Los componentes no llaman a `fetch` directamente: usan funciones de `features/<tema>/api.ts`.
- Todo dato que llega del backend se valida con Zod antes de usarse.
- Un archivo con `'use client'` solo puede exportar componentes a los de servidor.
  Las constantes y tipos compartidos van en un archivo aparte (ver `chartTheme.ts`).
- Los filtros y tabs viven en la URL (`?country=ARG&tab=labor`) para poder compartir vistas.
- Las etiquetas de estados (`trend_state_label`, `severity_label`) vienen traducidas
  del backend: no se duplican en el front.

---

## 7. Flujo de trabajo con Git

- `main` está protegida: no se hace push directo.
- Ramas: `feat/<tema>`, `fix/<tema>`, `docs/<tema>`. Ejemplo: `feat/ocupaciones-listado`.
- Commits en formato convencional: `feat(ocupaciones): listado con filtros`.
- Todo cambio entra por Pull Request con al menos una revisión.
- Al hacer `git add`, agregá solo tu carpeta (`git add frontend/`). Revisá `git status`
  antes de commitear para que no entren archivos del backend, `.env` ni `.venv`.
- Los cambios en componentes compartidos (`components/ui/`) van en PR chicos y se avisan
  al equipo, porque pueden afectar las pantallas de los demás.

---

## 8. División de tareas del equipo de frontend

Tres personas. Cada una es dueña de una zona del código para evitar pisarse.
Completar los nombres y marcar las tareas a medida que avanzan.

| | Persona | Zona |
|---|---|---|
| A | _(Eugwnia)_ | Datos, gráficos y base técnica |
| B | _(Betania)_ | Inicio, ocupaciones y alertas |
| C | _(Cheri)_ | Formación, páginas públicas y administración |

### Fase 0: base compartida (hacerla primero)

Las pantallas dependen de esto. Hasta que A cierre la capa de servicios, B y C pueden
avanzar con maquetado usando datos de ejemplo.

- [ ] **A.** Tokens de diseño de UX/UI en `globals.css` (colores, tipografía, espaciados).
- [ ] **A.** Capa de servicios: cliente HTTP en `lib/api/`, una función por endpoint con
  validación Zod, manejo de errores y alternancia mocks / API real.
- [ ] **A.** Configurar TanStack Query y nuqs (providers en el layout).
- [ ] **B.** Componentes de estado compartidos: `Skeleton`, `EmptyState`, `ErrorState`.
- [ ] **C.** Formateadores: fechas, números y porcentajes en formato es-AR, y cómo mostrar
  `data_type` (observado, calculado, proyectado).
- [ ] **C.** Guardar respuestas reales del backend como JSON en `src/mocks/`.
- [ ] **C.** GitHub Actions para el front: lint y build en cada PR (con `paths: frontend/**`).

### Fase 1: pantallas

**Persona A: datos y gráficos**

- [ ] Panorama regional conectada a la API: `/indicators`, `/dashboard/summary`, `/compare`,
  `/observations`.
- [ ] Tendencias y proyecciones: `/trends` y `/projections`, con línea punteada y banda
  sombreada (`lower_bound` / `upper_bound`).
- [ ] Panel "Ver fuente y metodología" con `/methodologies/{type}` (markdown).
- [ ] Gráficos reutilizables: barras por país, línea con banda de confianza.
- [ ] Estados `insufficient_data` y fuente desactualizada en gráficos y tendencias.

**Persona B: inicio, ocupaciones y alertas**

- [ ] Inicio: saludo, KPIs, accesos rápidos y feed de últimas novedades.
- [ ] Ocupaciones: listado con filtros y orden (`/employability`), con aviso de que el
  puntaje es relativo dentro de cada país.
- [ ] Detalle de ocupación (`/occupations/{code}`, `/employability/history`) con el desglose
  del puntaje por componentes.
- [ ] Ofertas laborales (`/jobs`, `/jobs/summary`): matriz provincia × sector y listado paginado.
- [ ] Campana de notificaciones (`/alerts`): contador, lista y marcar como leída mediante
  Route Handler con `x-api-key`.

**Persona C: formación, páginas públicas y administración**

- [ ] Home pública (landing): hero, qué podés encontrar, cómo funciona, demo y trazabilidad.
- [ ] Formación: tendencias y proyecciones de graduados (`/graduates/*`) y
  desajuste educativo (`/education-mismatch`).
- [ ] Brechas de habilidades (`/skills/gaps`, `/skills/{code}`), mostrando
  `data_sufficiency: none` sin inventar brechas.
- [ ] Administración: carga de datasets (`/datasets/upload` y `commit`), estado de fuentes y
  corridas (`/sources`), todo mediante Route Handlers.
- [ ] Login, registro y recuperar contraseña. **Bloqueado:** el backend no tiene
  autenticación todavía.

### Fase 2: calidad

- [ ] Responsive en celular y tablet de todas las pantallas (cada uno la suya).
- [ ] Accesibilidad: foco visible, contraste, navegación por teclado, textos alternativos.
- [ ] Tests: Vitest para utilidades y Playwright para los flujos principales.
- [ ] Rendimiento: revisar tamaño de gráficos y pedir al backend series ya agregadas.
- [ ] Storybook o una página `/dev/components` para validar fidelidad con UX/UI.

### Pendientes que desbloquean tareas (hablar con backend y UX/UI)

1. Autenticación y roles: quién la maneja (Supabase Auth o FastAPI) y si entra en el MVP.
2. Menú definitivo: el wireframe de Inicio y el de la landing muestran menús distintos.
3. Selección de países: ¿el filtro País es simple o múltiple?
4. Fecha de actualización de los datos de graduados, que hoy no viene en la API.
5. Campos en español en `/graduates/*` y `/jobs` (`pais`, `nombre`, `provincia`).
6. Alertas: `is_read` es global, no por usuario.
7. Wireframes faltantes: Ocupaciones, Formación, Brechas de habilidades, Administración
   y la pestaña "Proyecciones".

### Cómo no pisarnos

- Cada persona trabaja en su zona: `src/features/<tema>/` y su carpeta en `src/app/`.
- Antes de empezar una tarea, actualizá tu rama: `git pull origin main`.
- PR chicos y frecuentes; mejor tres PR de un día que uno de una semana.
- Si necesitás cambiar un componente compartido, avisá en el canal del equipo antes.
- Los esquemas de `lib/schemas/api.ts` los extiende quien necesite el endpoint, y el
  cambio va en el mismo PR que usa el esquema.

---
