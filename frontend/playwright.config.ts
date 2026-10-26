import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

const fixtureDirectory = path.resolve(process.cwd(), '../.test-data/browser')
const apiPort = process.env.GRIDBRICKS_TEST_API_PORT ?? '8000'
const webPort = process.env.GRIDBRICKS_TEST_WEB_PORT ?? '5174'
for (const port of [apiPort, webPort]) {
  if (!/^\d{1,5}$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
    throw new Error('Browser test ports must be valid local TCP ports')
  }
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'test-results/ui-results.json' }]],
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `../backend/.venv/bin/python -m gridbricks.cli ingest-fixtures && ../backend/.venv/bin/python -m uvicorn gridbricks.main:app --host 127.0.0.1 --port ${apiPort}`,
      env: { GRIDBRICKS_DATA_DIR: fixtureDirectory },
      url: `http://127.0.0.1:${apiPort}/api/v1/health`,
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
      timeout: 20000,
    },
    {
      command: `GRIDBRICKS_API_PORT=${apiPort} npm run dev -- --port ${webPort}`,
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
      timeout: 20000,
    },
  ],
})
