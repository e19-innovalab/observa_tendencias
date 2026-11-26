const { test, expect } = require('@playwright/test');

const fs = require('fs');
const path = require('path');

const archivo = path.join(__dirname, '..', 'usuario.json');
const local = fs.existsSync(archivo) ? JSON.parse(fs.readFileSync(archivo, 'utf-8')) : {};
const api = process.env.API_URL || local.api || 'http://127.0.0.1:8010';

test('el back responde', async ({ request }) => {
  const res = await request.get(`${api}/health`);
  expect(res.ok()).toBeTruthy();
  const data = await res.json();
  expect(data.status).toBe('ok');
});

test('estan los tres paises', async ({ request }) => {
  const res = await request.get(`${api}/api/v1/countries`);
  expect(res.ok()).toBeTruthy();
  const paises = (await res.json()).map((p) => p.iso3);
  expect(paises).toEqual(expect.arrayContaining(['ARG', 'CHL', 'URY']));
});

test('hay sectores cargados', async ({ request }) => {
  const res = await request.get(`${api}/api/v1/sectors`);
  expect(res.ok()).toBeTruthy();
  const sectores = await res.json();
  expect(sectores.length).toBeGreaterThan(0);
});
