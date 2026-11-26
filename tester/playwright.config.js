const { defineConfig } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const archivo = path.join(__dirname, 'usuario.json');
const local = fs.existsSync(archivo) ? JSON.parse(fs.readFileSync(archivo, 'utf-8')) : {};

module.exports = defineConfig({
  testDir: './tests',
  timeout: 90000,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.FRONT_URL || local.front || 'http://127.0.0.1:3000',
    screenshot: 'only-on-failure',
  },
});
