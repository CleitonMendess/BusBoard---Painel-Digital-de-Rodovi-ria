// Aba de plataformas: criar, editar, ativar/desativar e excluir.
import { useState } from 'react'
import { api, type Platform } from '../api'
import { readError, scrollToTop, type AbaProps } from '../comuns'

type AbaPlataformasProps = AbaProps & {
  plataformas: Platform[]
}

export default function AbaPlataformas({ plataformas, showNotification, refreshAllAdminData }: AbaPlataformasProps) {
  const [platformNumber, setPlatformNumber] = useState('')
  const [editingPlatformId, setEditingPlatformId] = useState<number | null>(null)

  function startEditPlatform(platform: Platform) {
    setEditingPlatformId(platform.id)
    setPlatformNumber(String(platform.number))
    scrollToTop()
  }

  function cancelEditPlatform() {
    setEditingPlatformId(null)
    setPlatformNumber('')
  }

  async function handleSavePlatform(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result =
        editingPlatformId === null
          ? await api.platforms.create({ number: Number(platformNumber), active: true })
          : await api.platforms.update(editingPlatformId, { number: Number(platformNumber) })
      showNotification('success', result.mensagem)
      cancelEditPlatform()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao salvar plataforma'))
    }
  }

  async function handleTogglePlatform(platform: Platform) {
    try {
      const result = await api.platforms.update(platform.id, { active: !platform.active })
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao alterar plataforma'))
    }
  }

  async function handleDeletePlatform(platform: Platform) {
    if (!window.confirm(`Excluir a plataforma ${platform.number}? Isso não pode ser desfeito.`)) return
    try {
      const result = await api.platforms.delete(platform.id)
      showNotification('success', result.mensagem)
      if (editingPlatformId === platform.id) cancelEditPlatform()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao excluir plataforma'))
    }
  }

  return (
    <div className="route-grid">
      <form className="route-card form-card" onSubmit={handleSavePlatform}>
        <div className="card-title-row">
          <h3>{editingPlatformId === null ? 'Criar plataforma' : 'Editar plataforma'}</h3>
        </div>
        <label>
          Número
          <input type="number" min="1" value={platformNumber} onChange={(event) => setPlatformNumber(event.target.value)} required />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit">
            {editingPlatformId === null ? 'Salvar plataforma' : 'Salvar alterações'}
          </button>
          {editingPlatformId !== null && (
            <button className="ghost-button" type="button" onClick={cancelEditPlatform}>Cancelar</button>
          )}
        </div>
      </form>

      <div className="route-card table-wrap">
        <div className="card-title-row">
          <h3>Plataformas cadastradas</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Número</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {plataformas.map((platform) => (
              <tr key={platform.id} className={platform.active ? '' : 'row-inactive'}>
                <td>{platform.number}</td>
                <td>{platform.active ? 'Ativa' : 'Inativa'}</td>
                <td>
                  <div className="row-actions">
                    <button type="button" className="mini-button" onClick={() => startEditPlatform(platform)}>Editar</button>
                    <button type="button" className="mini-button" onClick={() => handleTogglePlatform(platform)}>
                      {platform.active ? 'Desativar' : 'Ativar'}
                    </button>
                    <button type="button" className="mini-button danger" onClick={() => handleDeletePlatform(platform)}>Excluir</button>
                  </div>
                </td>
              </tr>
            ))}
            {plataformas.length === 0 && (
              <tr><td colSpan={3}>Nenhuma plataforma cadastrada</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
