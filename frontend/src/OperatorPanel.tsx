import { useCallback, useEffect, useState } from 'react'
import { api, type PendenteConfirmacao, type Trip } from './api'
import { useAvisosChegada, pendentesOrdenadas } from './useAvisosChegada'
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
  // viagem que o operador declarou não ter chegado: espera a nova previsão
  const [pedindoPrevisao, setPedindoPrevisao] = useState<PendenteConfirmacao | null>(null)
  const [novaPrevisao, setNovaPrevisao] = useState('')
  // viagem confirmada como presente na rodoviária: falta saber se já embarca
  const [perguntandoEmbarque, setPerguntandoEmbarque] = useState<PendenteConfirmacao | null>(null)
  const { pendentes, recarregar } = useAvisosChegada(true)

  const notify = useCallback((kind: Msg['kind'], text: string) => {
    setMsg({ kind, text })
    window.setTimeout(() => setMsg(null), 3500)
  }, [])

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

  const values = useCallback(
    (t: Row) => ({
      scheduled: edits[t.trip_id]?.scheduled ?? toInput(t.scheduled_time),
      estimated: edits[t.trip_id]?.estimated ?? toInput(t.estimated_time),
    }),
    [edits],
  )

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

  // "Chegou" grava NO HORARIO (o ônibus está lá) e pergunta se já está embarcando.
  // Sem gravar algo, a viagem continuaria pendente e o aviso voltaria em 20s.
  const registrarChegada = useCallback(
    async (p: PendenteConfirmacao) => {
      setSavingId(p.trip_id)
      try {
        await api.trips.updateStatus(p.trip_id, 'NO HORARIO')
        notify('success', `${p.destination}: ônibus confirmado`)
        setPerguntandoEmbarque(p)
        await load()
        await recarregar()
      } catch (e) {
        notify('error', e instanceof Error ? e.message : 'Falha ao confirmar chegada')
      } finally {
        setSavingId(null)
      }
    },
    [load, recarregar, notify],
  )

  const responderEmbarque = useCallback(
    async (embarcando: boolean) => {
      if (!perguntandoEmbarque) return
      const destino = perguntandoEmbarque.destination
      const id = perguntandoEmbarque.trip_id
      setPerguntandoEmbarque(null)
      setSavingId(id)
      try {
        if (embarcando) {
          await api.trips.updateStatus(id, 'EMBARQUE')
          notify('success', `${destino}: embarque iniciado`)
        } else {
          notify('success', `${destino}: aguardando embarque`)
        }
        await load()
        await recarregar()
      } catch (e) {
        notify('error', e instanceof Error ? e.message : 'Falha ao marcar embarque')
      } finally {
        setSavingId(null)
      }
    },
    [perguntandoEmbarque, load, recarregar, notify],
  )

  // "Não chegou": primeiro marca ATRASADO e depois pede a nova previsão, que é
  // gravada junto. Sem previsão o atraso fica sem informação na TV.
  const registrarAtraso = useCallback(async () => {
    if (!pedindoPrevisao) return
    if (!novaPrevisao) {
      notify('error', 'Informe a nova previsão de chegada')
      return
    }
    setSavingId(pedindoPrevisao.trip_id)
    try {
      const linha = rows.find((t) => t.trip_id === pedindoPrevisao.trip_id)
      await api.trips.updateTime(pedindoPrevisao.trip_id, {
        scheduled_time: linha ? values(linha).scheduled : pedindoPrevisao.scheduled_time,
        estimated_time: novaPrevisao,
      })
      await api.trips.updateStatus(pedindoPrevisao.trip_id, 'ATRASADO')
      notify('success', `${pedindoPrevisao.destination}: atraso registrado, nova previsão ${novaPrevisao}`)
      setPedindoPrevisao(null)
      setNovaPrevisao('')
      await load()
      await recarregar()
    } catch (e) {
      notify('error', e instanceof Error ? e.message : 'Falha ao registrar atraso')
    } finally {
      setSavingId(null)
    }
  }, [pedindoPrevisao, novaPrevisao, rows, load, recarregar, notify, values])

  const visibleRows = showFinished ? rows : rows.filter((t) => !HIDDEN.includes(t.status))
  const emAlerta = new Set(pendentes.map((p) => p.trip_id))

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

      {pendentes.length > 0 && (
        <div className="op-avisos" role="alert">
          <p className="op-avisos-titulo">
            {pendentes.length === 1
              ? '1 viagem passou do horário e precisa de confirmação'
              : `${pendentes.length} viagens passaram do horário e precisam de confirmação`}
          </p>
          <ul>
            {pendentesOrdenadas(pendentes).map((p) => (
              <li key={p.trip_id}>
                <div className="op-avisos-dados">
                  <strong>{p.destination}</strong>
                  <span>{p.scheduled_time}</span>
                  <span>{p.company}</span>
                </div>
                <div className="op-avisos-acoes">
                  <button
                    type="button"
                    className="ghost-button"
                    disabled={savingId === p.trip_id}
                    onClick={() => registrarChegada(p)}
                  >
                    Chegou
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => {
                      setPedindoPrevisao(p)
                      setNovaPrevisao('')
                    }}
                  >
                    Não chegou
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {perguntandoEmbarque && (
        <div className="op-avisos" role="dialog" aria-label="Confirmação de embarque">
          <p className="op-avisos-titulo">
            {perguntandoEmbarque.destination}: o ônibus já está embarcando?
          </p>
          <div className="op-avisos-form">
            <button
              type="button"
              className="primary-button"
              disabled={savingId === perguntandoEmbarque.trip_id}
              onClick={() => responderEmbarque(true)}
            >
              Sim, está embarcando
            </button>
            <button
              type="button"
              className="ghost-button"
              disabled={savingId === perguntandoEmbarque.trip_id}
              onClick={() => responderEmbarque(false)}
            >
              Ainda não
            </button>
          </div>
        </div>
      )}

      {pedindoPrevisao && (
        <div className="op-avisos" role="dialog" aria-label="Nova previsão de chegada">
          <p className="op-avisos-titulo">
            Nova previsão para {pedindoPrevisao.destination} (horário {pedindoPrevisao.scheduled_time})
          </p>
          <div className="op-avisos-form">
            <input
              type="time"
              value={novaPrevisao}
              onChange={(e) => setNovaPrevisao(e.target.value)}
              aria-label="Nova previsão de chegada"
            />
            <button
              type="button"
              className="primary-button"
              disabled={!novaPrevisao || savingId === pedindoPrevisao.trip_id}
              onClick={registrarAtraso}
            >
              {savingId === pedindoPrevisao.trip_id ? 'Salvando...' : 'Salvar como atrasado'}
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => {
                setPedindoPrevisao(null)
                setNovaPrevisao('')
              }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

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
                <tr
                  key={`${t.direction}-${t.trip_id}`}
                  className={emAlerta.has(t.trip_id) ? 'op-pendente' : undefined}
                >
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
