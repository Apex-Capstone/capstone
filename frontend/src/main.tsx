/**
 * Application entry: mounts the root React tree in strict mode.
 *
 * @remarks
 * Expects a DOM element with id `root` and loads global styles from `./index.css`.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
