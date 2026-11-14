const { test, expect } = require('@playwright/test');

const paginas = [
  '/inicio',
  '/panorama',
  '/sectores',
  '/ocupaciones',
  '/habilidades',
  '/pulso',
  '/moctezuma',
  '/metodologia/ise',
];

for (const ruta of paginas) {
  test(`la pagina ${ruta} carga`, async ({ page }) => {
    const res = await page.goto(ruta);
    expect(res.status()).toBeLessThan(400);
    await expect(page.locator('main')).not.toBeEmpty();
    await expect(page.getByText('Error inesperado')).toHaveCount(0);
  });
}

test('el menu lleva a cada seccion', async ({ page }) => {
  await page.goto('/inicio');
  const menu = page.getByRole('navigation', { name: 'Principal' });
  await menu.getByRole('link', { name: 'Sectores' }).click();
  await expect(page).toHaveURL(/\/sectores/);
  await menu.getByRole('link', { name: 'Ocupaciones' }).click();
  await expect(page).toHaveURL(/\/ocupaciones/);
});
