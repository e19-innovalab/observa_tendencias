# Testing

Acá están las pruebas del observatorio. Hay dos tipos:

- Pruebas manuales: se hacen a mano, recorriendo el sitio.
- Pruebas automáticas: las corre Playwright solo, sin tocar nada.

## Pruebas automáticas

Están hechas con Playwright y JavaScript, en la carpeta `tests`.

### api.spec.js

Prueba que el back responda bien:

- `/health` devuelve `status: ok`.
- `/api/v1/countries` trae Argentina, Chile y Uruguay.
- `/api/v1/sectors` trae al menos un sector.

### navegacion.spec.js

Prueba el front con un usuario logueado:

- Sin sesión, cualquier página manda al login.
- Con usuario y contraseña se entra al inicio.
- El botón de cerrar sesión vuelve al login.
- El saludo del inicio usa el nombre del usuario.
- Las 13 páginas del menú abren sin error y muestran contenido.
- El menú lleva a Sectores y a Género.
- El menú Experimentales se cierra al elegir una opción.
- Género muestra sus dos pestañas: titulados y ocupados.

### Cómo correrlas

Primero hay que tener levantados el back (puerto 8010) y el front (puerto 3000), y un usuario creado en el back (`python -m app.jobs.create_user`). El usuario de prueba se pone en un archivo `usuario.json` en esta carpeta, que no se sube a GitHub:

```json
{ "email": "tu@mail.com", "clave": "tu-contraseña" }
```

En WSL conviene levantar el front con `npm run dev < /dev/null`, porque si no Next puede cerrarse solo con la pregunta de actualizar versión.

Después, desde esta carpeta:

```bash
npm install
npx playwright install chromium
npm test
```

Para correr una sola parte:

```bash
npm run test:api
npm run test:front
```

Para probar el sitio publicado en vez del local, se agregan las dos direcciones en `usuario.json`:

```json
{
  "email": "tu@mail.com",
  "clave": "tu-contraseña",
  "front": "https://link-del-front",
  "api": "https://link-del-back"
}
```

Si no se ponen, se usa el front y el back locales. El usuario tiene que existir en el back que se prueba.

Al terminar, `npm run reporte` abre un reporte con el resultado de cada prueba. Si alguna falla, guarda una captura de la pantalla.

## Pruebas manuales

Cada prueba dice qué hacer y qué tiene que pasar.

### Generales

- Entrar al sitio. Carga en menos de un minuto.
- Entrar a cada sección del menú. Ninguna queda en blanco ni da error.
- Achicar la ventana a tamaño celular. El menú y los gráficos se acomodan.

### Panorama

- Elegir un indicador. Se ve el gráfico con los tres países.
- Cambiar el rango de años. El gráfico se actualiza.
- Cada gráfico dice la fuente y la fecha de actualización.

### Sectores y ocupaciones

- Elegir un sector. Se ven sus ocupaciones ordenadas por ISE.
- Abrir la ficha de una ocupación. Se ven el ISE por país y las habilidades.
- En la ficha, "Mostrar todas" despliega todas las habilidades, separadas en esenciales y opcionales.

### Habilidades

- Cambiar entre grupo de habilidades y habilidad detallada. Cambia la vista.
- Elegir un sector. Se actualiza la brecha.

### Experimental

- Abrir Moctezuma, Ludita, Reina Roja y Sísifo. Cada uno carga y tiene su explicación.

### Metodología

- Cada fuente tiene link y fecha de última descarga.

### Asistente

- Preguntar "¿cuánto cobra un remisero?". Responde y lleva a la ficha de conductores.
- Preguntar "¿cómo te llamás?". Responde que es Baquiano.

## Resultados

### 14/11/2026, en local

Se corrieron 12 pruebas: pasaron 9 y fallaron 3.

- API: las 3 pruebas pasaron.
- Navegación: pasaron inicio, sectores, ocupaciones, habilidades, metodología y el menú.
- Moctezuma: falla. La página muestra "Error inesperado al cargar los datos". El endpoint `/api/v1/moctezuma` existe en el back, así que puede faltar correr el cálculo del indicador en la base local. Queda para revisar con back.
- Panorama y Pulso laboral: cargan bien y con datos, pero no tienen un título principal (`h1`). No rompe nada, pero sí es un problema de accesibilidad, porque los lectores de pantalla usan ese título para saber de qué es la página. Se avisa a front.

Después de esto se cambió la prueba para que revise que la página tenga contenido en vez de buscar el `h1`, y lo del título quedó anotado como observación aparte.

### 19/11/2026, en local, con el front nuevo de main

Se corrieron 21 pruebas: pasaron 20 y falló 1.

- API: las 3 pasaron.
- Login: sin sesión manda al login, se puede entrar y cerrar sesión vuelve al login.
- Las 13 páginas cargan sin error.
- Falla el saludo: el inicio dice "¡Hola Santiago!" fijo en vez de usar el nombre del usuario.

Revisión del issue #41 y otros hallazgos:

- Login: no había desaparecido, faltaba el botón de cerrar sesión en el header. Se agregó en la rama `frontend/cerrar-sesion`.
- Moctezuma: no cargaba porque faltaba correr `python -m app.jobs.recompute`. Después de correrlo anda.
- Género, titulados por sexo: no cargaba porque faltaban las fuentes `universidades_egresados` y `carreras_seguimiento`. Después de cargarlas anda.
- Género, ocupados y salarios: sigue vacío. El back no tiene empleo por sexo de la OIT. Queda para back y data.
- Reina Roja: sin datos. Necesita al menos dos versiones de los perfiles de O*NET o ESCO. Queda para back y data.
- Género no avisa cuando no tiene datos, a diferencia de Reina Roja.
- El menú Experimentales queda abierto después de elegir una opción.
- Género tiene el aviso de Next por `connection()` fuera de `<Suspense>`.
- Si se cargan datos nuevos, el front puede mostrar los viejos hasta una hora, por la caché de `fetch`.
- Back: `alembic upgrade head` falla en las migraciones 0019 y 0020 porque la 0017 crea `skill_groups` desde el modelo actual, que ya trae esas columnas y ese índice. Habría que agregarles el mismo chequeo que tienen la 0026 en adelante.

### 19/11/2026, segunda corrida, después de los arreglos

Los bugs del front se arreglaron en la rama `frontend/arreglos-testing`:

- El saludo del inicio ahora usa el nombre del usuario.
- El menú Experimentales se cierra al elegir una opción.
- Género muestra "Todavía no hay datos..." cuando una tabla está vacía.
- Género ya no tiene el aviso de `connection()` fuera de `<Suspense>`.

Se sumaron dos pruebas, una para el menú y otra para el aviso de Género. Se corrieron 23 pruebas y pasaron las 23.

Quedan pendientes para back y data:

- Reina Roja sin datos (faltan versiones de O*NET o ESCO).
- Género sin ocupados por sexo (falta empleo por sexo de la OIT).
- Migraciones 0019 y 0020.

### 26/11/2026, contra el sitio publicado (MVP)

Se corrieron las pruebas contra el front publicado en Vercel (https://predix-silk.vercel.app) y el back de Render, con el front nuevo ya unido a main.

Antes de correrlas se actualizaron tres pruebas por cambios del front:

- El login ahora tiene el botón para ver la contraseña, así que la prueba busca el campo exacto.
- El menú Experimentales ahora es un panel de dos columnas.
- Género ahora tiene dos pestañas, así que la prueba entra a Titulados y después a Ocupados.

Se corrieron 23 pruebas y pasaron las 23.

- API: las 3 pasaron.
- Login: sin sesión manda al login, se puede entrar y cerrar sesión vuelve al login.
- El saludo usa el nombre del usuario.
- Las 13 páginas cargan sin error.
- El menú lleva a cada sección y Experimentales se cierra al elegir.
- Género muestra sus dos pestañas.

Observaciones:

- El back de Render está en el plan gratis y se duerme cuando no se usa. El primer ingreso puede tardar hasta un minuto en contestar, por eso la prueba de login espera hasta 60 segundos.
- En una corrida, un ingreso tardó más de un minuto y pasó en el segundo intento. Si se va a mostrar la página en una presentación, conviene abrirla un rato antes para que el back se despierte.
