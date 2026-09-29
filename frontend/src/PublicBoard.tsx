import { useEffect, useMemo, useRef, useState } from 'react'
import { api, type Trip } from './api'
import './PublicBoard.css'

const PAGE_SIZE = 8
const POLL_MS = 30_000
const PAGE_MS = 10_000
const STALE_RELOAD_MS = 15 * 60_000

const STATUS_LABEL: Record<string, string> = {
  AGENDADO: 'Agendado',
  'NO HORARIO': 'No horário',
  EMBARQUE: 'Embarque',
  ATRASADO: 'Atrasado',
  CANCELADO: 'Cancelado',
  SAIU: 'Saiu',
  CHEGOU: 'Chegou',
}

// Aceita "08:30", "08:30:00" e "08:30 AM"/"2:15 PM". Qualquer outra coisa ("30m") vira ''.
const hhmm = (t?: string | null) => {
  const m = t?.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i)
  if (!m) return ''
  let h = Number(m[1])
  const ap = m[3]?.toUpperCase()
  if (ap === 'PM' && h < 12) h += 12
  if (ap === 'AM' && h === 12) h = 0
  if (h > 23 || Number(m[2]) > 59) return ''
  return `${String(h).padStart(2, '0')}:${m[2]}`
}
const toMin = (t: string) => {
  if (!t) return Number.POSITIVE_INFINITY
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}
const effectiveTime = (t: Trip) => hhmm(t.estimated_time) || hhmm(t.scheduled_time)

// Esconde o que já acabou e o que passou há mais de 30 min; ordena pelo horário real.
function visibleTrips(trips: Trip[], nowMin: number) {
  return trips
    .filter((t) => {
      if (t.status === 'SAIU' || t.status === 'CHEGOU') return false
      if (t.status === 'EMBARQUE' || t.status === 'ATRASADO') return true
      return toMin(effectiveTime(t)) >= nowMin - 30
    })
    .sort((a, b) => toMin(effectiveTime(a)) - toMin(effectiveTime(b)))
}

function Board({ title, place, trips, now }: { title: string; place: string; trips: Trip[]; now: Date }) {
  const pages = Math.max(1, Math.ceil(trips.length / PAGE_SIZE))
  const page = Math.floor(now.getTime() / PAGE_MS) % pages
  const rows = trips.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <section className="tv-board">
      <header className="tv-board-head">
        <h2>{title}</h2>
        {pages > 1 && (
          <span className="tv-pages">
            {page + 1}/{pages}
          </span>
        )}
      </header>
      <div className="tv-cols">
        <span>Horário</span>
        <span>{place}</span>
        <span>Plataforma</span>
        <span>Situação</span>
      </div>
      <ul className="tv-rows">
        {rows.map((t) => {
          const est = hhmm(t.estimated_time)
          const delayed = !!est && est !== hhmm(t.scheduled_time)
          const cls = t.status.toLowerCase().replace(/\s+/g, '-')
          return (
            <li key={t.trip_id ?? t.id} className={`tv-row tv-${cls}`}>
              <span className="tv-time">
                {delayed && <s>{hhmm(t.scheduled_time)}</s>}
                <b>{effectiveTime(t)}</b>
              </span>
              <span className="tv-dest">
                <b>{t.destination}</b>
                <small>{t.company}</small>
              </span>
              <span className="tv-plat">{t.platform}</span>
              <span className="tv-status">{STATUS_LABEL[t.status] ?? t.status}</span>
            </li>
          )
        })}
        {rows.length === 0 && <li className="tv-empty">Sem horários no momento</li>}
      </ul>
    </section>
  )
}

export default function PublicBoard() {
  const [departures, setDepartures] = useState<Trip[]>([])
  const [arrivals, setArrivals] = useState<Trip[]>([])
  const [now, setNow] = useState(new Date())
  const [offline, setOffline] = useState(false)
  const lastOk = useRef(Date.now())

  useEffect(() => {
    const tick = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(tick)
  }, [])

  useEffect(() => {
    async function load() {
      try {
        const [d, a] = await Promise.all([api.board.departures(), api.board.arrivals()])
        setDepartures(d.saidas)
        setArrivals(a.chegadas)
        setOffline(false)
        lastOk.current = Date.now()
      } catch {
        setOffline(true)
        // refresh de segurança: ~15 min sem receber dados, recarrega a página
        if (Date.now() - lastOk.current > STALE_RELOAD_MS) window.location.reload()
      }
    }
    load()
    const poll = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(poll)
  }, [])

  const nowMin = now.getHours() * 60 + now.getMinutes()
  const deps = useMemo(() => visibleTrips(departures, nowMin), [departures, nowMin])
  const arrs = useMemo(() => visibleTrips(arrivals, nowMin), [arrivals, nowMin])

  return (
    <div className="tv">
      <header className="tv-top">
        <div className="tv-clock">
          {now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </div>
        <div className="tv-date">
          {now.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </div>
        {offline && <div className="tv-offline">Sem conexão. Mostrando os últimos horários recebidos.</div>}
      </header>
      <main className="tv-boards">
        <Board title="Saídas" place="Destino" trips={deps} now={now} />
        <Board title="Chegadas" place="Origem" trips={arrs} now={now} />
      </main>
    </div>
  )
}
