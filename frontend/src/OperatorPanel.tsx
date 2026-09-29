import { useCallback, useEffect, useState } from 'react'
import { api, type Trip } from './api'
import './OperatorPanel.css'

type Row = Trip & { direction: 'Saída' | 'Chegada' }
type Msg = { kind: 'success' | 'error'; text: string }

const HIDDEN = ['SAIU', 'CHEGOU', 'CANCELADO']

const STATUS_OPTIONS = ['AGENDADO', 'NO HORARIO', 'EMBARQUE', 'ATRASADO', 'CANCELADO', 'SAIU', 'CHEGOU']

// Converte "08:30", "08:30:00" ou "2:15 PM" em "HH:MM" (formato do input type=time).
function toInput(t?: string | null) {
  const m = t?.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i)
  if (!m) return ''
  let h = Number(m[1])
  const ap = m[3]?.toUpperCase()
  if (ap === 'PM' && h < 12) h += 12
  if (ap === 'AM' && h === 12) h = 0
  return `${String(h).padStart(2, '0')}:${m[2]}`
}

export default function OperatorPanel({ embedded = false }: { embedded?: boolean }) {
  const [rows, setRows] = useState<Row[]>([])
  const [edits, setEdits] = useState<Record<number, { scheduled: string; estimated: string }>>({})
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [showFinished, setShowFinished] = useState(false)
  const [msg, setMsg] = useState<Msg | null>(null)

  const notify = (kind: Msg['kind'], text: string) => {
    setMsg({ kind, text })
    window.setTimeout(() => setMsg(null), 3500)
  }

  const load = useCallback(async () => {
    try {
      const [d, a] = await Promise.all([api.board.departures(), api.board.arrivals()])
      const all: Row[] = [
        ...d.saidas.map((t) => ({ ...t, direction: 'Saída' as const })),
        ...a.chegadas.map((t) => ({ ...t, direction: 'Chegada' as const })),
      ]
      setRows(all.sort((x, y) => toInput(x.scheduled_time).localeCompare(toInput(y.scheduled_time))))
      setEdits({})
    } catch (e) {
      setMsg({ kind: 'error', text: e instanceof Error ? e.message : 'Erro ao carregar viagens' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const values = (t: Row) => ({
    scheduled: edits[t.trip_id]?.scheduled ?? toInput(t.scheduled_time),
    estimated: edits[t.trip_id]?.estimated ?? toInput(t.estimated_time),
  })

  const change = (t: Row, key: 'scheduled' | 'estimated', value: string) =>
    setEdits((prev) => ({ ...prev, [t.trip_id]: { ...values(t), ...prev[t.trip_id], [key]: value } }))

  const isDirty = (t: Row) => {
    const v = values(t)
    return v.scheduled !== toInput(t.scheduled_time) || v.estimated !== toInput(t.estimated_time)
  }

  async function save(t: Row) {
    const v = values(t)
    if (!v.scheduled) {
      notify('error', 'Informe o horário da viagem')
      return
    }
    setSavingId(t.trip_id)
    try {
      const res = await api.trips.updateTime(t.trip_id, {
        scheduled_time: v.scheduled,
        estimated_time: v.estimated, // vazio = tira a previsão
      })
      notify('success', res.mensagem)
      await load()
    } catch (e) {
      notify('error', e instanceof Error ? e.message : 'Falha ao salvar horário')
    } finally {
      setSavingId(null)
    }
  }

  async function changeStatus(t: Row, status: string) {
    if (status === t.status) return
    setSavingId(t.trip_id)
    try {
      const res = await api.trips.updateStatus(t.trip_id, status)
      notify('success', `${t.destination}: ${res.status_atual}`)
      await load()
    } catch (e) {
      notify('error', e instanceof Error ? e.message : 'Falha ao mudar status')
    } finally {
      setSavingId(null)
    }
  }

  const visibleRows = showFinished ? rows : rows.filter((t) => !HIDDEN.includes(t.status))

  return (
    <section className="op-panel">
      <div className="admin-topline">
        <div>
          <p className="eyebrow">{embedded ? 'Operação do dia' : 'Painel do operador'}</p>
          <h2>Viagens de hoje</h2>
        </div>
        <button type="button" className="ghost-button" onClick={load}>
          Atualizar
        </button>
      </div>

      {msg && <div className={`notice ${msg.kind}`}>{msg.text}</div>}

      <label className="op-toggle">
        <input type="checkbox" checked={showFinished} onChange={(e) => setShowFinished(e.target.checked)} />
        Mostrar viagens encerradas (saiu, chegou, cancelado)
      </label>

      <div className="route-card table-wrap">
        {loading ? (
          <div className="loading">Carregando viagens...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Sentido</th>
                <th>Destino / origem</th>
                <th>Empresa</th>
                <th>Horário</th>
                <th>Previsão</th>
                <th></th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((t) => (
                <tr key={`${t.direction}-${t.trip_id}`}>
                  <td>{t.direction}</td>
                  <td>{t.destination}</td>
                  <td>{t.company}</td>
                  <td>
                    <input
                      className="op-time"
                      type="time"
                      value={values(t).scheduled}
                      onChange={(e) => change(t, 'scheduled', e.target.value)}
                      aria-label={`Horário de ${t.destination}`}
                    />
                  </td>
                  <td>
                    <input
                      className="op-time"
                      type="time"
                      value={values(t).estimated}
                      onChange={(e) => change(t, 'estimated', e.target.value)}
                      aria-label={`Previsão de ${t.destination}`}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="primary-button"
                      disabled={!isDirty(t) || savingId === t.trip_id}
                      onClick={() => save(t)}
                    >
                      {savingId === t.trip_id ? 'Salvando...' : 'Salvar'}
                    </button>
                  </td>
                  <td>
                    <select
                      className={`op-time op-status op-status-${t.status.toLowerCase().replace(/\s+/g, '-')}`}
                      value={t.status}
                      disabled={savingId === t.trip_id}
                      onChange={(e) => changeStatus(t, e.target.value)}
                      aria-label={`Situação de ${t.destination}`}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {visibleRows.length === 0 && (
                <tr>
                  <td colSpan={7}>Nenhuma viagem para ajustar agora</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
