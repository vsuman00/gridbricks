import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const decisionUrl = '/?decision_date=2026-01-15&cutoff=09%3A30'

test('the workspace serves stored data and rejects the retired preview link', async ({ page }) => {
  await page.goto(decisionUrl)
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open UI preview' })).toHaveCount(0)
  await expect(page.getByText('UI PREVIEW')).toHaveCount(0)
  await page.goto('/?mode=preview')
  await expect(page.getByRole('alert')).toContainText('unsupported filters')
  await expect(page.getByRole('region', { name: 'Delivery interval templates' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Reset link' }).click()
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await expect(page).not.toHaveURL(/mode=preview/)
})

test('a changed cutoff is identified as applied while the demo default stays clear', async ({ page }) => {
  await page.goto(decisionUrl)
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await page.getByLabel('Buying cutoff · UK time').fill('09:00')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await expect(page.locator('.scope-note')).toContainText(
    'Applied cutoff: 09:00 UK · Demo default: 09:30 UK.',
  )
  await expect(page.getByRole('link', { name: 'Export CSV' })).toHaveAttribute(
    'href',
    /cutoff=09%3A00/,
  )
})

test('date-range validation, navigation, and history preserve real results', async ({ page }) => {
  await page.goto(decisionUrl)
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await page.getByRole('button', { name: 'Accuracy' }).click()
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await page.getByLabel('Decision from').fill('2026-01-16')
  await page.getByLabel('Decision to').fill('2026-01-15')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByText('Choose an end date on or after the start date.')).toBeVisible()
  await expect(page.getByLabel('Decision to')).toHaveAttribute('aria-invalid', 'true')
  await page.getByLabel('Decision from').fill('2026-01-15')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await expect(page).toHaveURL(/decision_from=2026-01-15/)
  await page.goBack()
  await expect(page.getByLabel('Decision from')).toHaveValue('2026-01-01')
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Wind outlook', level: 1 })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
})

test('keyboard links and data details dialog work with stored status', async ({ page }) => {
  await page.goto(decisionUrl)
  await expect(page.getByRole('region', { name: 'Delivery interval observations' })).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main')).toBeFocused()
  await page.getByRole('link', { name: /View table/ }).click()
  await expect(page.locator('#intervals')).toBeFocused()
  const opener = page.getByRole('button', { name: 'Sources & methodology' })
  await opener.click()
  const dialog = page.getByRole('dialog', { name: 'Data details' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('API connected', { exact: true })).toBeVisible()
  await expect(dialog.getByText('Synthetic fixture', { exact: true })).toBeVisible()
  await dialog.evaluate((element) =>
    Promise.all(element.getAnimations().map((animation) => animation.finished)),
  )
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([])
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(opener).toBeFocused()
})

test('stored chart motion is finite and disabled by reduced motion', async ({ page }) => {
  await page.goto(decisionUrl)
  const curve = page.locator('.data-plot .forecast-curve')
  await expect(curve).toBeVisible()
  const duration = await curve.evaluate((element) =>
    Number.parseFloat(getComputedStyle(element).animationDuration),
  )
  expect(duration).toBeGreaterThan(0)
  expect(duration).toBeLessThanOrEqual(0.7)
  expect(
    await page.evaluate(() =>
      document
        .getAnimations()
        .some((animation) => animation.effect?.getComputedTiming().iterations === Infinity),
    ),
  ).toBe(false)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.reload()
  await expect(curve).toBeVisible()
  expect(await page.evaluate(() => document.getAnimations().length)).toBe(0)
})
