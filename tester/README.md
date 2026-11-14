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

Prueba que el front cargue bien:

- Cada página del menú abre sin error y muestra contenido.
- Ninguna página muestra el mensaje "Error inesperado".
- El menú lleva a Sectores y a Ocupaciones.

### Cómo correrlas

Primero hay que tener levantados el back (puerto 8010) y el front (puerto 3000). Después, desde esta carpeta:

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

Para probar el sitio publicado en vez del local:

```bash
FRONT_URL=https://link-del-front API_URL=https://link-del-back npm test
```

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
