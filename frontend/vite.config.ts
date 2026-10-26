import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
}

// Internal loopback test/runtime port; never a browser-supplied upstream URL.
const apiPort = process.env.GRIDBRICKS_API_PORT ?? '8000'
if (!/^\d{1,5}$/.test(apiPort) || Number(apiPort) < 1 || Number(apiPort) > 65535) {
  throw new Error('GRIDBRICKS_API_PORT must be a valid local TCP port')
}
const apiTarget = `http://127.0.0.1:${apiPort}`

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    headers: securityHeaders,
    proxy: { '/api': apiTarget },
  },
  preview: {
    proxy: { '/api': apiTarget },
    headers: {
      ...securityHeaders,
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'",
    },
  },
})
