const { test, expect } = require('@playwright/test');

const fs = require('fs');
const path = require('path');

const archivo = path.join(__dirname, '..', 'usuario.json');
const local = fs.existsSync(archivo) ? JSON.parse(fs.readFileSync(archivo, 'utf-8')) : {};
const email = process.env.TEST_EMAIL || local.email;
const clave = process.env.TEST_PASSWORD || local.clave;
const nombre = process.env.TEST_NAME || local.nombre;

const paginas = [
  '/inicio',
  '/panorama-regional',
  '/sectores',
  '/ocupaciones',
  '/habilidades',
  '/genero',
  '/pulso',
  '/moctezuma',
  '/ludita',
  '/reina-roja',
  '/sisifo',
  '/metodologia/ise',
  '/alertas',
];

async function entrar(page) {
  await page.goto('/login');
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña', { exact: true }).fill(clave);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page).toHaveURL(/\/inicio/, { timeout: 60000 });
}

test('sin sesion lleva al login', async ({ page }) => {
  await page.goto('/inicio');
  await expect(page).toHaveURL(/\/login/);
});

test('con usuario y clave entra', async ({ page }) => {
  await entrar(page);
  await expect(page.getByRole('button', { name: 'Cerrar sesión' })).toBeVisible();
});

test('cerrar sesion vuelve al login', async ({ page }) => {
  await entrar(page);
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto('/inicio');
  await expect(page).toHaveURL(/\/login/);
});

test('el saludo usa el nombre del usuario', async ({ page }) => {
  await entrar(page);
  const saludo = page.getByRole('heading', { level: 1 });
  if (nombre) await expect(saludo).toContainText(nombre);
  else await expect(saludo).toHaveText(/¡Hola \S+!/);
  await expect(saludo).not.toContainText('Santiago');
});

for (const ruta of paginas) {
  test(`la pagina ${ruta} carga`, async ({ page }) => {
    await entrar(page);
    const res = await page.goto(ruta);
    expect(res.status()).toBeLessThan(400);
    await expect(page.locator('main')).not.toBeEmpty();
    await expect(page.getByText('Error inesperado')).toHaveCount(0);
  });
}

test('el menu lleva a cada seccion', async ({ page }) => {
  await entrar(page);
  const menu = page.getByRole('navigation', { name: 'Principal' });
  await menu.getByRole('link', { name: 'Sectores' }).click();
  await expect(page).toHaveURL(/\/sectores/);
  await menu.getByRole('link', { name: 'Género' }).click();
  await expect(page).toHaveURL(/\/genero/);
});

test('el menu experimentales se cierra al elegir', async ({ page }) => {
  await entrar(page);
  const menu = page.getByRole('navigation', { name: 'Principal' });
  const lista = menu.locator('details[data-menu]').filter({ visible: true });
  await lista.locator('summary').click();
  await lista.getByRole('link', { name: /Moctezuma/ }).click();
  await expect(page).toHaveURL(/\/moctezuma/);
  await expect(lista).not.toHaveAttribute('open', '');
});

test('genero muestra las dos secciones', async ({ page }) => {
  await entrar(page);
  await page.goto('/genero');
  await expect(page.getByRole('heading', { name: 'Titulados por sexo' })).toBeVisible();
  await page.getByRole('link', { name: 'Personas ocupadas y salarios' }).click();
  await expect(page).toHaveURL(/tab=ocupados/);
  await expect(page.getByRole('heading', { name: 'Personas ocupadas y salarios' })).toBeVisible();
});
