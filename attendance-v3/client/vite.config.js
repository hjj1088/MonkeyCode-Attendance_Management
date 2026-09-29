import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const SPA_PREFIXES = [
  '/login',
  '/setup',
  '/my',
  '/import',
  '/attendance',
  '/export',
  '/users',
  '/settings',
]

function spaHtmlFallback() {
  return {
    name: 'spa-html-fallback',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const raw = req.url || ''
        const url = raw.split('?')[0]
        if (url.includes('.')) return next()
        const hit = SPA_PREFIXES.some((p) => url === p || url.startsWith(p + '/'))
        if (hit) {
          const qs = raw.includes('?') ? raw.slice(raw.indexOf('?')) : ''
          req.url = '/index.html' + qs
        }
        next()
      })
    },
  }
}

export default defineConfig({
  appType: 'spa',
  plugins: [spaHtmlFallback(), vue()],
  server: {
    port: 8002,
    allowedHosts: ['.monkeycode-ai.online'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      }
    }
  }
})
