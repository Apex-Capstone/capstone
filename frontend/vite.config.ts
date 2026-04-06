/**
 * Vite configuration for the React frontend.
 *
 * @remarks
 * Configures the React plugin and the `@` path alias to `./src` for imports.
 *
 * @see https://vite.dev/config/
 */
/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    setupFiles: ['./src/test/vitest-setup.ts', './src/test/setup.ts'],
  },
})
