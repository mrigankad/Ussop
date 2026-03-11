import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  const isProd = mode === 'production'

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
    build: {
      outDir: path.resolve(__dirname, '../static/dist'),
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks: {
            react:   ['react', 'react-dom', 'react-router-dom'],
            charts:  ['chart.js', 'react-chartjs-2'],
            icons:   ['@phosphor-icons/react'],
            radix:   [
              '@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu',
              '@radix-ui/react-tabs', '@radix-ui/react-toast',
              '@radix-ui/react-select', '@radix-ui/react-tooltip',
            ],
          },
        },
      },
    },
    base: isProd ? '/static/dist/' : '/',
    server: {
      port: 5173,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true },
        '/static/images': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      },
    },
  }
})
