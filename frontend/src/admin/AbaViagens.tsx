// Aba de viagens: criar, editar, mudar status, excluir e reiniciar o dia.
import { useState } from 'react'
import { api, type Company, type Destination, type Platform, type Trip } from '../api'
import {
  directionOptions,
  formatTime,
  readError,
  scrollToTop,
  statusClassMap,
  statusOptions,
  type AbaProps,
  type TripDirection,
  type TripStatus,
  typeOptions,
  type TripType,
} from '../comuns'

type AbaViagensProps = AbaProps & {
  viagens: Trip[]
  empresas: Company[]
  destinos: Destination[]
  plataformas: Platform[]
}

const emptyTripForm = {
  type: 'INTERESTADUAL',
  trip_direction: 'SAIDA' as TripDirection,
  scheduled_time: '',
  estimated_time: '',
  status: 'AGENDADO' as TripStatus,
  company_id: '',
  destination_id: '',
  platform_id: '',
}

export default function AbaViagens({
  viagens,
  empresas,
  destinos,
  plataformas,
  showNotification,
  refreshAllAdminData,
}: AbaViagensProps) {
  const [tripForm, setTripForm] = useState(emptyTripForm)
  const [editingTripId, setEditingTripId] = useState<number | null>(null)

  function startEditTrip(trip: Trip) {
    setEditingTripId(trip.trip_id ?? trip.id ?? null)
    setTripForm({
      type: trip.type || 'INTERESTADUAL',
      trip_direction: (trip.trip_direction as TripDirection) || 'SAIDA',
      scheduled_time: trip.scheduled_time || '',
      estimated_time: trip.estimated_time || '',
      status: (trip.status as TripStatus) || 'AGENDADO',
      company_id: trip.company_id ? String(trip.company_id) : '',
      destination_id: trip.destination_id ? String(trip.destination_id) : '',
      platform_id: trip.platform_id ? String(trip.platform_id) : '',
    })
    scrollToTop()
  }

  function cancelEditTrip() {
    setEditingTripId(null)
    setTripForm(emptyTripForm)
  }

  async function handleSaveTrip(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      let mensagem: string
      if (editingTripId === null) {
        const result = await api.trips.create({
          type: tripForm.type,
          trip_direction: tripForm.trip_direction,
          scheduled_time: tripForm.scheduled_time,
          estimated_time: tripForm.estimated_time || undefined,
          status: tripForm.status,
          company_id: Number(tripForm.company_id),
          destination_id: Number(tripForm.destination_id),
          platform_id: Number(tripForm.platform_id),
        })
        mensagem = result.mensagem
      } else {
        const result = await api.trips.update(editingTripId, {
          type: tripForm.type,
          trip_direction: tripForm.trip_direction,
          scheduled_time: tripForm.scheduled_time,
          estimated_time: tripForm.estimated_time, // '' remove a previsão
          status: tripForm.status,
          company_id: Number(tripForm.company_id),
          destination_id: Number(tripForm.destination_id),
          platform_id: Number(tripForm.platform_id),
        })
        mensagem = result.mensagem
      }
      showNotification('success', mensagem)
      cancelEditTrip()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao salvar viagem'))
    }
  }

  async function handleResetDay() {
    if (!window.confirm('Reiniciar o dia?\n\nTodas as viagens voltam para AGENDADO e as previsões de horário são apagadas. Os horários programados continuam iguais.')) return
    try {
      const result = await api.trips.resetDay()
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao reiniciar o dia'))
    }
  }

  async function handleDeleteTrip(trip: Trip) {
    const id = trip.trip_id ?? trip.id
    if (id === undefined) return
    if (!window.confirm(`Excluir a viagem das ${trip.scheduled_time} para ${trip.destination}? Isso não pode ser desfeito.`)) return
    try {
      const result = await api.trips.delete(id)
      showNotification('success', result.mensagem)
      if (editingTripId === id) cancelEditTrip()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao excluir viagem'))
    }
  }

  async function handleChangeTripStatus(tripId: number, status: TripStatus) {
    try {
      const result = await api.trips.updateStatus(tripId, status)
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao atualizar status'))
    }
  }

  return (
    <div className="route-grid trips-layout">
      <form className="route-card form-card" onSubmit={handleSaveTrip}>
        <div className="card-title-row">
          <h3>{editingTripId === null ? 'Criar viagem' : 'Editar viagem'}</h3>
        </div>
        <label>
          Tipo
          <select
            value={tripForm.type}
            onChange={(event) => setTripForm({ ...tripForm, type: event.target.value as TripType })}
            required
          >
            {typeOptions.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Direção
          <select
            value={tripForm.trip_direction}
            onChange={(event) => setTripForm({ ...tripForm, trip_direction: event.target.value as TripDirection })}
          >
            {directionOptions.map((direction) => (
              <option key={direction} value={direction}>{direction}</option>
            ))}
          </select>
        </label>
        <label>
          Horário
          <input type="time" value={tripForm.scheduled_time} onChange={(event) => setTripForm({ ...tripForm, scheduled_time: event.target.value })} required />
        </label>
        <label>
          Previsão
          <input type="time" value={tripForm.estimated_time} onChange={(event) => setTripForm({ ...tripForm, estimated_time: event.target.value })} />
        </label>
        <label>
          Status
          <select value={tripForm.status} onChange={(event) => setTripForm({ ...tripForm, status: event.target.value as TripStatus })}>
            {statusOptions.map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
        </label>
        <label>
          Empresa
          <select value={tripForm.company_id} onChange={(event) => setTripForm({ ...tripForm, company_id: event.target.value })} required>
            <option value="">Selecione</option>
            {empresas
              .filter((company) => company.active || String(company.id) === tripForm.company_id)
              .map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}{company.active ? '' : ' (inativa)'}
                </option>
              ))}
          </select>
        </label>
        <label>
          Destino
          <select value={tripForm.destination_id} onChange={(event) => setTripForm({ ...tripForm, destination_id: event.target.value })} required>
            <option value="">Selecione</option>
            {destinos
              .filter((destination) => destination.active || String(destination.id) === tripForm.destination_id)
              .map((destination) => (
                <option key={destination.id} value={destination.id}>
                  {destination.city}/{destination.state}{destination.active ? '' : ' (inativo)'}
                </option>
              ))}
          </select>
        </label>
        <label>
          Plataforma
          <select value={tripForm.platform_id} onChange={(event) => setTripForm({ ...tripForm, platform_id: event.target.value })} required>
            <option value="">Selecione</option>
            {plataformas
              .filter((platform) => platform.active || String(platform.id) === tripForm.platform_id)
              .map((platform) => (
                <option key={platform.id} value={platform.id}>
                  {platform.number}{platform.active ? '' : ' (inativa)'}
                </option>
              ))}
          </select>
        </label>

        <div className="form-actions">
          <button className="primary-button" type="submit">
            {editingTripId === null ? 'Salvar viagem' : 'Salvar alterações'}
          </button>
          {editingTripId !== null && (
            <button className="ghost-button" type="button" onClick={cancelEditTrip}>Cancelar</button>
          )}
        </div>
      </form>

      <div className="route-card table-wrap trip-table-card">
        <div className="card-title-row">
          <h3>Viagens cadastradas</h3>
          <button type="button" className="mini-button danger" onClick={handleResetDay} title="O sistema também faz isso sozinho todo dia de madrugada">
            Reiniciar o dia
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Empresa</th>
              <th>Horário</th>
              <th>Destino</th>
              <th>Plataforma</th>
              <th>Status</th>
              <th>Mudar status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {viagens.map((trip) => (
              <tr key={trip.trip_id ?? trip.id}>
                <td>{trip.type || '-'}</td>
                <td>{trip.company || '-'}</td>
                <td>
                  {formatTime(trip.scheduled_time)}
                  {trip.estimated_time && trip.estimated_time !== trip.scheduled_time && (
                    <small className="estimated-hint"> → {trip.estimated_time}</small>
                  )}
                </td>
                <td>{trip.destination}</td>
                <td>{trip.platform}</td>
                <td>
                  <span className={`status-badge ${statusClassMap[trip.status as TripStatus] || ''}`}>
                    {trip.status}
                  </span>
                </td>
                <td>
                  <select
                    value={trip.status}
                    onChange={(event) => handleChangeTripStatus(trip.trip_id ?? trip.id ?? 0, event.target.value as TripStatus)}
                  >
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                </td>
                <td>
                  <div className="row-actions">
                    <button type="button" className="mini-button" onClick={() => startEditTrip(trip)}>Editar</button>
                    <button type="button" className="mini-button danger" onClick={() => handleDeleteTrip(trip)}>Excluir</button>
                  </div>
                </td>
              </tr>
            ))}
            {viagens.length === 0 && (
              <tr><td colSpan={8}>Nenhuma viagem cadastrada</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
