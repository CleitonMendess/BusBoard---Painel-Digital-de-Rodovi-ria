import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import PublicBoard from './PublicBoard.tsx'

// A TV abre /painel: tela cheia, sem nada de admin.
const isBoard = window.location.pathname.replace(/\/$/, '') === '/painel'

createRoot(document.getElementById('root')!).render(
  <StrictMode>{isBoard ? <PublicBoard /> : <App />}</StrictMode>,
)
