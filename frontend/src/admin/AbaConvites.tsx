// Convites de cadastro.
//
// Criar conta é pelo convite, não por um cadastro aberto: quem tem o link cria
// a conta com a função que o ADM escolheu aqui, e o link só funciona uma vez.
import { useEffect, useState } from 'react'
import { api, type CreatedInvite, type Invite } from '../api'
import { readError, type AbaProps } from '../comuns'

type AbaConvitesProps = AbaProps

const SITUACAO_ROTULO: Record<Invite['situacao'], string> = {
  pendente: 'Pendente',
  usado: 'Usado',
  expirado: 'Expirado',
}

function quando(iso: string): string {
  const data = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`)
  if (Number.isNaN(data.getTime())) return iso
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

export default function AbaConvites({ showNotification }: AbaConvitesProps) {
  const [convites, setConvites] = useState<Invite[]>([])
  const [role, setRole] = useState('operador')
  const [validade, setValidade] = useState('72')
  const [criado, setCriado] = useState<CreatedInvite | null>(null)

  async function carregar() {
    try {
      setConvites((await api.invites.list()).Convites)
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao carregar os convites'))
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const resultado = await api.invites.create(role, Number(validade) || undefined)
      // o código aparece só agora: é a única chance de copiar
      setCriado(resultado)
      await carregar()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar o convite'))
    }
  }

  function copiar(convite: CreatedInvite) {
    const link = `${window.location.origin}${convite.link}`
    navigator.clipboard
      ?.writeText(link)
      .then(() => showNotification('success', 'Link copiado. Agora é só enviar para a pessoa.'))
      .catch(() => showNotification('error', `Copie na mão: ${link}`))
  }

  async function handleCancel(convite: Invite) {
    if (!window.confirm('Cancelar este convite? Quem tiver o link não vai conseguir criar a conta.')) return
    try {
      const resultado = await api.invites.cancel(convite.id)
      showNotification('success', resultado.mensagem)
      await carregar()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao cancelar o convite'))
    }
  }

  return (
    <div className="route-grid users-layout">
      <form className="route-card form-card" onSubmit={handleCreate}>
        <div className="card-title-row">
          <h3>Gerar convite</h3>
        </div>

        <label>
          Função da conta
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="operador">Operador</option>
            <option value="adm">Administrador</option>
          </select>
        </label>

        <label>
          Validade (horas)
          <input
            type="number"
            min={1}
            max={2160}
            value={validade}
            onChange={(event) => setValidade(event.target.value)}
          />
        </label>

        <button className="primary-button" type="submit">Gerar convite</button>

        {criado && (
          <div className="notice success invite-novo">
            <strong>Link criado:</strong>
            <code>{`${window.location.origin}${criado.link}`}</code>
            <div className="row-actions">
              <button type="button" className="mini-button" onClick={() => copiar(criado)}>
                Copiar link
              </button>
            </div>
            <small>{criado.aviso}</small>
          </div>
        )}
      </form>

      <div className="route-card table-wrap">
        <div className="card-title-row">
          <h3>Convites</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Função</th>
              <th>Criado em</th>
              <th>Vence em</th>
              <th>Situação</th>
              <th>Usado por</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {convites.map((convite) => (
              <tr key={convite.id} className={convite.situacao === 'pendente' ? '' : 'row-inactive'}>
                <td>{convite.role === 'adm' ? 'Administrador' : 'Operador'}</td>
                <td>{quando(convite.created_at)}</td>
                <td>{quando(convite.expires_at)}</td>
                <td>{SITUACAO_ROTULO[convite.situacao]}</td>
                <td>{convite.usado_por ?? '—'}</td>
                <td>
                  {convite.situacao === 'pendente' ? (
                    <button type="button" className="mini-button danger" onClick={() => handleCancel(convite)}>
                      Cancelar
                    </button>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
            {convites.length === 0 && (
              <tr><td colSpan={6}>Nenhum convite ainda</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
