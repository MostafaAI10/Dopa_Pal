import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'

export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        // Main process — vite-plugin-electron will launch electron once
        entry: 'src/main/main.js',
        vite: {
          build: {
            rollupOptions: {
              external: ['better-sqlite3']
            }
          }
        },
        onstart(options) {
          // startup() launches electron with VITE_DEV_SERVER_URL set correctly
          options.startup();
        },
      },
      {
        // Preload — just reload on change, don't launch again
        entry: 'src/main/preload.js',
        onstart(options) {
          options.reload();
        },
      },
    ]),
  ],
  css: {
    postcss: null,  // no postcss/tailwind
  },
})
