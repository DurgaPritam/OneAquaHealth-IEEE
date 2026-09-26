/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// BASE_PATH lets the static demo build live under a sub-path (for example GitHub Pages).
export default defineConfig({
  base: process.env.BASE_PATH ?? '/',
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'AquaSentinel',
        short_name: 'AquaSentinel',
        description: 'Citizen stream checks for mosquito habitat risk',
        theme_color: '#053a30',
        background_color: '#f8fafc',
        display: 'standalone',
        start_url: '.',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,json}'],
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        runtimeCaching: [
          { urlPattern: ({ url }) => url.pathname.startsWith('/api/sites'), handler: 'StaleWhileRevalidate', options: { cacheName: 'sites' } },
          { urlPattern: ({ url }) => url.hostname.endsWith('tile.openstreetmap.org'), handler: 'CacheFirst', options: { cacheName: 'tiles', expiration: { maxEntries: 500 } } },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: { '/api': `http://127.0.0.1:${process.env.API_PORT ?? '8000'}` },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.tsx'],
    css: false,
    globals: true,
  },
})
