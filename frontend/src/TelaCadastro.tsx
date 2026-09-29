// Tela de cadastro por convite.
//
// A tela de login é só para entrar. Quem chega aqui tem um código que o
// administrador mandou; o papel da conta vem do convite, não do que a pessoa
// digita aqui.
import { useEffect, useState } from 'react'
import { api, saveSession, type InviteCheck } from './api'
import { readError } from './comuns'

type TelaCadastroProps = {
  token: string
  onPronto: (role: string) => void
}

const FORM_VAZIO = { name: '', email: '', password: '', confirmacao: '' }

export default function TelaCadastro({ token, onPronto }: TelaCadastroProps) {
  const [checagem, setChecagem] = useState<InviteCheck | null>(null)
  const [form, setForm] = useState(FORM_VAZIO)
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  // conferindo o código antes de mostrar o formulário: melhor avisar na hora
  // que o convite venceu do que deixar a pessoa preencher tudo para nada
  useEffect(() => {
    let cancelado = false
    api.invites
      .check(token)
      .then((resposta) => {
        if (!cancelado) setChecagem(resposta)
      })
      .catch((e) => {
        if (!cancelado) setChecagem({ valido: false, motivo: readError(e, 'Convite inválido') })
      })
    return () => {
      cancelado = true
    }
  }, [token])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro('')

    if (form.password !== form.confirmacao) {
      setErro('As senhas não são iguais')
      return
    }

    setEnviando(true)
    try {
      const result = await api.register({
        token,
        name: form.name,
        email: form.email,
        password: form.password,
      })
      // conta criada e já logada: não faz sentido pedir a senha de novo
      saveSession(result.access_token, result.refresh_token, result.role)
      onPronto(result.role)
    } catch (e) {
      setErro(readError(e, 'Não consegui criar a conta'))
    } finally {
      setEnviando(false)
    }
  }

  if (checagem === null) {
    return (
      <div className="login-card">
        <p className="eyebrow">BusBoard</p>
        <h2>Conferindo o convite…</h2>
      </div>
    )
  }

  if (!checagem.valido) {
    return (
      <div className="login-card">
        <div className="login-header">
          <div>
            <p className="eyebrow">Convite</p>
            <h2>Não dá para criar a conta</h2>
          </div>
        </div>
        <div className="login-error">{checagem.motivo}</div>
        <p className="login-hint">
          Peça um novo convite a quem administra o sistema. Cada convite vale uma
          conta só e tem prazo de validade.
        </p>
        <div className="form-actions">
          <button type="button" className="ghost-button" onClick={() => { window.location.href = '/' }}>
            Voltar para o login
          </button>
        </div>
      </div>
    )
  }

  const ehAdm = checagem.role === 'adm'

  return (
    <div className="login-card">
      <div className="login-header">
        <div>
          <p className="eyebrow">Convite válido</p>
          <h2>Criar minha conta</h2>
        </div>
      </div>

      <p className="login-hint">
        Você vai entrar como <strong>{ehAdm ? 'administrador' : 'operador'}</strong>,
        conforme o convite recebido.
      </p>

      <form onSubmit={handleSubmit} className="login-form">
        {erro && <div className="login-error">{erro}</div>}

        <label>
          Nome
          <input
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            placeholder="Como te chamamos"
            required
          />
        </label>

        <label>
          E-mail
          <input
            type="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            placeholder="voce@exemplo.com"
            required
          />
        </label>

        <label>
          Senha
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            placeholder="Pelo menos 8 caracteres"
            minLength={8}
            required
          />
        </label>

        <label>
          Repita a senha
          <input
            type="password"
            value={form.confirmacao}
            onChange={(event) => setForm({ ...form, confirmacao: event.target.value })}
            placeholder="De novo, para não ter erro"
            minLength={8}
            required
          />
        </label>

        <div className="form-actions">
          <button type="submit" className="primary-button" disabled={enviando}>
            {enviando ? 'Criando conta…' : 'Criar conta e entrar'}
          </button>
          <button type="button" className="ghost-button" onClick={() => { window.location.href = '/' }}>
            Voltar para o login
          </button>
        </div>
      </form>
    </div>
  )
}
