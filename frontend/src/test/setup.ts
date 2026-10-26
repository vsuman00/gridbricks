import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)

// jsdom does not implement the browser's top-layer modal behavior. Native focus
// trapping and Escape handling are verified with Playwright, not this stand-in.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () { this.open = true }
}
if (!HTMLDialogElement.prototype.close) {
  HTMLDialogElement.prototype.close = function () {
    this.open = false
    this.dispatchEvent(new Event('close'))
  }
}
