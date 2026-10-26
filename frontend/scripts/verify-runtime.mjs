/* global document, innerWidth, PerformanceObserver, requestAnimationFrame, performance, fetch, console, URL */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import os from 'node:os'
import process from 'node:process'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'
import { chromium } from '@playwright/test'

const frontend = fileURLToPath(new URL('..', import.meta.url))
const evidence = new URL('../../docs/evidence/ui/', import.meta.url)
const url = 'http://127.0.0.1:4184'
const dataDir = fileURLToPath(new URL('../../data/fixtures/', import.meta.url))
const backend = spawn(
  fileURLToPath(new URL('../../backend/.venv/bin/python', import.meta.url)),
  [
    '-m',
    'uvicorn',
    'gridbricks.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    '4185',
    '--no-access-log',
  ],
  {
    cwd: frontend,
    env: { ...process.env, GRIDBRICKS_DATA_DIR: dataDir },
    stdio: ['ignore', 'pipe', 'pipe'],
  },
)
const server = spawn(
  process.execPath,
  [
    'node_modules/vite/bin/vite.js',
    'preview',
    '--host',
    '127.0.0.1',
    '--port',
    '4184',
    '--strictPort',
  ],
  {
    cwd: frontend,
    env: { ...process.env, GRIDBRICKS_API_PORT: '4185' },
    stdio: ['ignore', 'pipe', 'pipe'],
  },
)
let output = ''
server.stdout.on('data', (chunk) => {
  output += chunk
})
server.stderr.on('data', (chunk) => {
  output += chunk
})
backend.stdout.on('data', (chunk) => {
  output += chunk
})
backend.stderr.on('data', (chunk) => {
  output += chunk
})
let browser
const report = {
  checked_at_utc: new Date().toISOString(),
  scope:
    'Production UI with real local API and isolated synthetic snapshot; analytical API benchmark recorded separately.',
  environment: {
    node: process.version,
    platform: process.platform,
    arch: process.arch,
    machine: os.cpus()[0]?.model,
  },
  assets: [],
  cases: [],
}

try {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (backend.exitCode !== null) throw new Error(output)
    try {
      const status = await fetch('http://127.0.0.1:4185/api/v1/data-status')
      const data = await status.json()
      if (data.snapshot?.source_mode === 'fixture') {
        report.fixture_snapshot_id = data.snapshot.snapshot_id
        break
      }
      throw new Error('Run make ingest-fixtures before production runtime checks')
    } catch (error) {
      if (error.message?.includes('ingest-fixtures')) throw error
    }
    await delay(100)
  }
  assert(report.fixture_snapshot_id, `Owned fixture API did not start: ${output}`)
  let response
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(output)
    try {
      response = await fetch(url)
      if (response.ok) break
    } catch {
      /* Await owned preview startup. */
    }
    await delay(100)
  }
  assert(response?.ok, `Preview did not start: ${output}`)
  report.headers = Object.fromEntries(response.headers)
  for (const [name, value] of [
    ['x-content-type-options', 'nosniff'],
    ['x-frame-options', 'DENY'],
    ['referrer-policy', 'no-referrer'],
  ]) {
    assert.equal(response.headers.get(name), value)
  }
  const csp = response.headers.get('content-security-policy')
  for (const directive of [
    "default-src 'self'",
    "script-src 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
  ])
    assert(csp?.includes(directive))
  assert(!csp.includes('unsafe-inline') && !csp.includes('unsafe-eval'))

  for (const name of await readdir(new URL('../dist/assets/', import.meta.url))) {
    const bytes = await readFile(new URL(`../dist/assets/${name}`, import.meta.url))
    const asset = {
      name,
      bytes: bytes.length,
      gzip_bytes: gzipSync(bytes).length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
    }
    report.assets.push(asset)
    if (name.endsWith('.js')) assert(asset.gzip_bytes < 100_000, 'JS gzip exceeds 100KB UI budget')
    if (name.endsWith('.css'))
      assert(asset.gzip_bytes < 10_000, 'Styles gzip exceeds 10KB UI budget')
  }

  browser = await chromium.launch()
  for (const view of ['decision', 'accuracy']) {
    for (const width of [320, 768, 1024, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } })
      const problems = []
      const external = []
      page.on('pageerror', (error) => problems.push(error.message))
      page.on('console', (message) => {
        if (message.type() === 'error') problems.push(message.text())
      })
      page.on('request', (request) => {
        if (!request.url().startsWith(url)) external.push(request.url())
      })
      await page.addInitScript(() => {
        globalThis.__uiMetrics = { cls: 0, longTasks: [], shifts: [] }
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries())
            if (!entry.hadRecentInput) {
              globalThis.__uiMetrics.cls += entry.value
              globalThis.__uiMetrics.shifts.push({
                value: entry.value,
                elements: (entry.sources ?? []).map((source) => ({
                  element: source.node?.className?.toString(),
                  previous: { y: source.previousRect.y, height: source.previousRect.height },
                  current: { y: source.currentRect.y, height: source.currentRect.height },
                })),
              })
            }
        }).observe({ type: 'layout-shift', buffered: true })
        new PerformanceObserver((list) => {
          globalThis.__uiMetrics.longTasks.push(...list.getEntries().map((entry) => entry.duration))
        }).observe({ type: 'longtask', buffered: true })
      })
      await page.goto(`${url}/?view=${view}`, { waitUntil: 'load' })
      await page
        .getByRole('heading', {
          name: view === 'decision' ? 'Wind outlook' : 'Forecast accuracy',
          exact: true,
        })
        .waitFor()
      await page.locator('.data-plot').waitFor()
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      const frameGaps = await page.evaluate(
        () =>
          new Promise((resolve) => {
            const gaps = []
            let previous = performance.now()
            const start = previous
            function frame(now) {
              gaps.push(now - previous)
              previous = now
              if (now - start < 800) requestAnimationFrame(frame)
              else resolve(gaps)
            }
            requestAnimationFrame(frame)
          }),
      )
      const metrics = await page.evaluate(() => {
        const nav = performance.getEntriesByType('navigation')[0]
        return {
          ...globalThis.__uiMetrics,
          dcl_ms: nav.domContentLoadedEventEnd,
          load_ms: nav.loadEventEnd,
          overflow: document.documentElement.scrollWidth > innerWidth,
          running_animations: document
            .getAnimations()
            .filter((animation) => animation.playState === 'running').length,
        }
      })
      const sorted = frameGaps.sort((a, b) => a - b)
      const frameP95 = sorted[Math.floor(sorted.length * 0.95)]
      const caseReport = {
        view,
        width,
        ...metrics,
        frame_gap_p95_ms: frameP95,
        external_requests: external.length,
        browser_errors: problems,
      }
      report.cases.push(caseReport)
      assert.equal(metrics.overflow, false, `Page overflow ${view}/${width}`)
      assert.equal(metrics.running_animations, 0, 'Animation remains running after entrance')
      assert(metrics.cls < 0.05, `Unexpected initial layout shift: ${metrics.cls}`)
      assert(frameP95 < 50, `Frame gap p95 ${frameP95}ms exceeds local 50ms threshold`)
      assert(metrics.dcl_ms < 1500, 'Local document readiness exceeds 1.5s threshold')
      assert.deepEqual(external, [], 'Unexpected external asset request')
      assert.deepEqual(problems, [], 'Production browser errors')
      await page.close()
    }
  }
  const probe = await browser.newPage()
  await probe.goto(url)
  let blocked = false
  try {
    await probe.addScriptTag({ content: 'globalThis.__inlineSecurityProbe = true' })
  } catch {
    blocked = true
  }
  assert(
    blocked && !(await probe.evaluate(() => globalThis.__inlineSecurityProbe)),
    'Inline script was not blocked by CSP',
  )
  report.inline_script_blocked = true
  report.status = 'passed'
} catch (error) {
  report.status = 'failed'
  report.failure = String(error)
  process.exitCode = 1
} finally {
  await browser?.close()
  server.kill('SIGTERM')
  backend.kill('SIGTERM')
  await mkdir(evidence, { recursive: true })
  await writeFile(
    new URL('production-runtime.json', evidence),
    `${JSON.stringify(report, null, 2)}\n`,
  )
}
console.log(
  JSON.stringify(
    {
      status: report.status,
      cases: report.cases.length,
      failure: report.failure,
      assets: report.assets,
    },
    null,
    2,
  ),
)
