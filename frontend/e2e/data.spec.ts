import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

const analyticalUrl = '/?decision_date=2026-01-15&cutoff=09%3A30'
const intervalRegion = 'Delivery interval observations'
const apiBase = `http://127.0.0.1:${process.env.GRIDBRICKS_TEST_API_PORT ?? '8000'}`

test('stored fixture replay selects the eligible vintage and exposes lineage without actual leakage', async ({
  page,
}) => {
  const requests: string[] = []
  page.on('request', (request) => requests.push(request.url()))
  await page.goto(analyticalUrl)
  const table = page.getByRole('region', { name: intervalRegion })
  await expect(table).toBeVisible()
  await expect(page.getByText('Synthetic fixture dataset.', { exact: false })).toBeVisible()
  await expect(table.getByRole('row').nth(1).getByRole('cell').nth(0)).toHaveText('100')
  await expect(page.getByRole('columnheader', { name: 'Actual reference · MW' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Forecast error', exact: true })).toHaveCount(0)
  await expect(page).toHaveURL(/snapshot_id=/)
  await table.getByText('Inspect source records', { exact: true }).first().click()
  await expect(table.getByText(/fixture:\/\/synthetic\//).first()).toBeVisible()
  await page.getByRole('button', { name: 'Show all 24 intervals' }).click()
  await expect(table.getByRole('row')).toHaveCount(25)
  await expect(table.getByText('forecast conflict', { exact: true })).toBeVisible()
  expect(requests.every((url) => new URL(url).hostname === '127.0.0.1')).toBe(true)
})

test('retrospective metrics and reference labels come from the pinned API response', async ({
  page,
  request,
}) => {
  await page.goto('/?view=accuracy&decision_from=2026-01-15&decision_to=2026-01-15&cutoff=09%3A30')
  await expect(page.getByRole('region', { name: intervalRegion })).toBeVisible()
  const query = new URL(page.url()).searchParams
  const snapshot = query.get('snapshot_id')!
  const response = await request.get(
    `${apiBase}/api/v1/accuracy?decision_from=2026-01-15&decision_to=2026-01-15&cutoff=09:30&snapshot_id=${snapshot}`,
  )
  const data = await response.json()
  await expect(page.getByRole('columnheader', { name: 'Actual reference · MW' })).toBeVisible()
  await expect(page.getByRole('note')).toContainText('physical averaging equivalence is unverified')
  const metricCard = page.locator('.metric').filter({ hasText: 'Mean absolute error · MAE' })
  await expect(metricCard.locator('.metric-value')).toContainText(
    new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 }).format(data.metrics.mae_mw),
  )
  await expect(page.getByText('Retrospective comparison', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Daily accuracy observations' })).toContainText(
    '23 / 24',
  )
  const row = page.getByRole('region', { name: intervalRegion }).getByRole('row').nth(1)
  await expect(row.getByRole('cell').nth(0)).toHaveText('100')
  await expect(row.getByRole('cell').nth(1)).toHaveText('0')
  await expect(row.getByRole('cell').nth(2)).toHaveText('+100')
})

test('a slower old cutoff cannot replace the most recently applied query', async ({ page }) => {
  let release!: () => void
  let oldStarted!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  const started = new Promise<void>((resolve) => {
    oldStarted = resolve
  })
  await page.route('**/api/v1/forecast?**', async (route) => {
    const upstream = await route.fetch()
    if (new URL(route.request().url()).searchParams.get('cutoff') === '09:30') {
      oldStarted()
      await held
    }
    await route.fulfill({ response: upstream }).catch(() => {})
  })
  await page.goto('/?decision_date=2026-01-15&cutoff=10%3A30')
  const firstValue = () =>
    page
      .getByRole('region', { name: intervalRegion })
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(0)
  await expect(firstValue()).toHaveText('140')
  await page.getByLabel(/Buying cutoff/).fill('09:30')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await started
  await page.getByLabel(/Buying cutoff/).fill('10:30')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(firstValue()).toHaveText('140')
  release()
  await expect(page.getByLabel(/Buying cutoff/)).toHaveValue('10:30')
  await expect(firstValue()).toHaveText('140')
  await expect(page).toHaveURL(/cutoff=10%3A30/)
})

test('an unknown pinned snapshot has explicit recovery and disables export', async ({ page }) => {
  await page.goto(analyticalUrl + '&snapshot_id=missing-snapshot')
  await expect(page.getByRole('heading', { name: 'Selected snapshot unavailable' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
  await page.getByRole('button', { name: 'Use active snapshot' }).click()
  await expect(page.getByRole('region', { name: intervalRegion })).toBeVisible()
  await expect(page).not.toHaveURL(/snapshot_id=missing-snapshot/)
  await expect(page.getByRole('link', { name: 'Export CSV' })).toBeVisible()
})

test('API failure and an absent stored dataset have distinct truthful states', async ({ page }) => {
  await page.route('**/api/v1/data-status**', (route) =>
    route.fulfill({
      status: 200,
      json: {
        snapshot: null,
        last_import: null,
        alignment: { verified: false, policy: null, message: 'No stored inputs' },
        sources: [],
      },
    }),
  )
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'No stored dataset' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
  await page.unroute('**/api/v1/data-status**')
  await page.route('**/api/v1/data-status**', (route) => route.abort('internetdisconnected'))
  await page.getByRole('button', { name: 'Refresh dataset status' }).click()
  await expect(page.getByRole('heading', { name: 'Data request failed' })).toBeVisible()
  await expect(page.getByText(/could not be reached/)).toBeVisible()
})

test('CSV download uses the displayed snapshot and reproduces forecast table values', async ({
  page,
  request,
}) => {
  await page.goto(analyticalUrl)
  const exportLink = page.getByRole('link', { name: 'Export CSV' })
  await expect(exportLink).toBeVisible()
  const snapshot = new URL(page.url()).searchParams.get('snapshot_id')!
  const analysis = await request.get(
    `${apiBase}/api/v1/forecast?decision_date=2026-01-15&cutoff=09:30&snapshot_id=${snapshot}`,
  )
  const data = await analysis.json()
  const downloadPromise = page.waitForEvent('download')
  await exportLink.click()
  const download = await downloadPromise
  const file = await download.path()
  expect(file).not.toBeNull()
  const rows = parseCsv(await readFile(file!, 'utf8'))
  expect(rows).toHaveLength(24)
  for (const [index, row] of rows.entries()) {
    expect(row.snapshot_id).toBe(snapshot)
    expect(row.target_start).toBe(data.rows[index].target_start)
    expect(row.state).toBe(data.rows[index].state)
    expect(row.forecast_mw === '' ? null : Number(row.forecast_mw)).toBe(
      data.rows[index].forecast_mw,
    )
  }
})

test('reload preserves stored view, snapshot and cutoff', async ({ page }) => {
  await page.goto(analyticalUrl)
  await expect(page.getByRole('region', { name: intervalRegion })).toBeVisible()
  const snapshot = new URL(page.url()).searchParams.get('snapshot_id')
  await page.reload()
  await expect(page.getByRole('region', { name: intervalRegion })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('snapshot_id')).toBe(snapshot)
  await expect(page.getByLabel(/Buying cutoff/)).toHaveValue('09:30')
  await expect(page.getByRole('button', { name: 'Open UI preview' })).toHaveCount(0)
})

for (const width of [320, 768, 1024, 1440]) {
  for (const view of ['decision', 'accuracy']) {
    test(`stored ${view} is responsive and passes axe at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 })
      await page.goto(
        view === 'decision'
          ? analyticalUrl
          : '/?view=accuracy&decision_from=2026-01-15&decision_to=2026-01-15',
      )
      await expect(page.getByRole('region', { name: intervalRegion })).toBeVisible()
      const sizes = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
      }))
      expect(sizes.scroll).toBeLessThanOrEqual(sizes.client)
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      expect(results.violations).toEqual([])
    })
  }
}

function parseCsv(text: string): Record<string, string>[] {
  const records: string[][] = []
  let row: string[] = [],
    field = '',
    quoted = false
  for (let i = 0; i < text.length; i += 1) {
    const value = text[i]
    if (value === '"') {
      if (quoted && text[i + 1] === '"') {
        field += '"'
        i += 1
      } else quoted = !quoted
    } else if (!quoted && (value === ',' || value === '\n')) {
      row.push(field.replace(/\r$/, ''))
      field = ''
      if (value === '\n') {
        records.push(row)
        row = []
      }
    } else field += value
  }
  if (field || row.length) records.push([...row, field])
  const [header, ...rows] = records
  return rows.map((record) =>
    Object.fromEntries(header.map((name, index) => [name, record[index]])),
  )
}
