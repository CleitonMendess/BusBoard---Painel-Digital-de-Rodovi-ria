import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import PublicBoard from './PublicBoard.tsx'
import TelaCadastro from './TelaCadastro.tsx'

// O caminho diz o que abrir, sem roteador: o painel é a raiz, a TV da rodoviária
// é /painel e o cadastro por convite é /cadastro/<codigo>.
const caminho = window.location.pathname.replace(/\/$/, '')

function tokenDoConvite(): string | null {
  if (!caminho.startsWith('/cadastro')) return null
  const token = caminho.replace('/cadastro/', '')
  return token || null
}

const token = tokenDoConvite()
const isBoard = caminho === '/painel'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {token ? (
      <TelaCadastro
        token={token}
        onPronto={() => {
          // conta criada e sessão salva: o painel assume a partir daqui
          window.location.href = '/'
        }}
      />
    ) : isBoard ? (
      <PublicBoard />
    ) : (
      <App />
    )}
  </StrictMode>,
)
