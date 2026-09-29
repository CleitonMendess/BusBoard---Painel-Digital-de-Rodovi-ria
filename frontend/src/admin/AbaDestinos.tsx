// Aba de destinos: criar, editar, ativar/desativar e excluir.
import { useState } from 'react'
import { api, type Destination } from '../api'
import { readError, scrollToTop, type AbaProps } from '../comuns'

type AbaDestinosProps = AbaProps & {
  destinos: Destination[]
}

const FORM_VAZIO = {
  city: '',
  state: '',
  active: true,
}

export default function AbaDestinos({ destinos, showNotification, refreshAllAdminData }: AbaDestinosProps) {
  const [destinationForm, setDestinationForm] = useState(FORM_VAZIO)
  const [editingDestinationId, setEditingDestinationId] = useState<number | null>(null)

  function startEditDestination(destination: Destination) {
    setEditingDestinationId(destination.id)
    setDestinationForm({ city: destination.city, state: destination.state, active: destination.active })
    scrollToTop()
  }

  function cancelEditDestination() {
    setEditingDestinationId(null)
    setDestinationForm(FORM_VAZIO)
  }

  async function handleSaveDestination(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result =
        editingDestinationId === null
          ? await api.destinations.create(destinationForm)
          : await api.destinations.update(editingDestinationId, destinationForm)
      showNotification('success', result.mensagem)
      cancelEditDestination()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao salvar destino'))
    }
  }

  async function handleToggleDestination(destination: Destination) {
    try {
      const result = await api.destinations.update(destination.id, { active: !destination.active })
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao alterar destino'))
    }
  }

  async function handleDeleteDestination(destination: Destination) {
    if (!window.confirm(`Excluir o destino "${destination.city}/${destination.state}"? Isso não pode ser desfeito.`)) return
    try {
      const result = await api.destinations.delete(destination.id)
      showNotification('success', result.mensagem)
      if (editingDestinationId === destination.id) cancelEditDestination()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao excluir destino'))
    }
  }

  return (
    <div className="route-grid">
      <form className="route-card form-card" onSubmit={handleSaveDestination}>
        <div className="card-title-row">
          <h3>{editingDestinationId === null ? 'Criar destino' : 'Editar destino'}</h3>
        </div>
        <label>
          Cidade
          <input value={destinationForm.city} onChange={(event) => setDestinationForm({ ...destinationForm, city: event.target.value })} required />
        </label>
        <label>
          Estado
          <input value={destinationForm.state} onChange={(event) => setDestinationForm({ ...destinationForm, state: event.target.value })} required />
        </label>
        <label className="switch-row">
          <input
            type="checkbox"
            checked={destinationForm.active}
            onChange={(event) => setDestinationForm({ ...destinationForm, active: event.target.checked })}
          />
          Destino ativo
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit">
            {editingDestinationId === null ? 'Salvar destino' : 'Salvar alterações'}
          </button>
          {editingDestinationId !== null && (
            <button className="ghost-button" type="button" onClick={cancelEditDestination}>Cancelar</button>
          )}
        </div>
      </form>

      <div className="route-card table-wrap">
        <div className="card-title-row">
          <h3>Destinos cadastrados</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Cidade</th>
              <th>Estado</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {destinos.map((destination) => (
              <tr key={destination.id} className={destination.active ? '' : 'row-inactive'}>
                <td>{destination.id}</td>
                <td>{destination.city}</td>
                <td>{destination.state}</td>
                <td>{destination.active ? 'Ativo' : 'Inativo'}</td>
                <td>
                  <div className="row-actions">
                    <button type="button" className="mini-button" onClick={() => startEditDestination(destination)}>Editar</button>
                    <button type="button" className="mini-button" onClick={() => handleToggleDestination(destination)}>
                      {destination.active ? 'Desativar' : 'Ativar'}
                    </button>
                    <button type="button" className="mini-button danger" onClick={() => handleDeleteDestination(destination)}>Excluir</button>
                  </div>
                </td>
              </tr>
            ))}
            {destinos.length === 0 && (
              <tr><td colSpan={5}>Nenhum destino cadastrado</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
