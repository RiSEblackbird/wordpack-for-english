import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from '@playwright/test';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(currentDir, '../..');
const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173';

export default defineConfig({
  testDir: currentDir,
  fullyParallel: true,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  reporter: [
    ['list'],
    [
      'html',
      {
        open: 'never',
        outputFolder: path.join(repoRoot, 'playwright-report'),
      },
    ],
  ],
  outputDir: path.join(repoRoot, 'test-results'),
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        'python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --app-dir apps/backend',
      url: 'http://127.0.0.1:8000/healthz',
      reuseExistingServer: !process.env.CI,
      cwd: repoRoot,
      timeout: 120_000,
      env: {
        // E2E の実行時はローカル API を確実に参照させ、Vite のプロキシ先を固定する。
        BACKEND_PROXY_TARGET: 'http://127.0.0.1:8000',
        FIRESTORE_EMULATOR_HOST: process.env.FIRESTORE_EMULATOR_HOST ?? '127.0.0.1:8080',
        FIRESTORE_PROJECT_ID: process.env.FIRESTORE_PROJECT_ID ?? 'wordpack-ci',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      cwd: path.join(repoRoot, 'apps/frontend'),
      timeout: 120_000,
    },
  ],
});
