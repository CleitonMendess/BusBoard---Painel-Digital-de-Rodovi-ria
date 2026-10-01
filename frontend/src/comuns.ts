// Tipos, constantes e funções que as abas do painel compartilham.
import type { Trip } from './api'

export type TripDirection = 'SAIDA' | 'CHEGADA'

export type TripStatus =
  | 'AGENDADO'
  | 'NO HORARIO'
  | 'EMBARQUE'
  | 'ATRASADO'
  | 'CANCELADO'
  | 'SAIU'
  | 'CHEGOU'

export type View = 'public' | 'login' | 'users' | 'convites' | 'companies' | 'destinations' | 'platforms' | 'trips' | 'operation'

export type AdminTab = 'overview' | 'operation' | 'users' | 'convites' | 'companies' | 'destinations' | 'platforms' | 'trips'

export type Notification = {
  kind: 'success' | 'error'
  message: string
}

export const statusClassMap: Record<TripStatus, string> = {
  AGENDADO: 'status-agendado',
  'NO HORARIO': 'status-no-horario',
  EMBARQUE: 'status-embarque',
  ATRASADO: 'status-atrasado',
  CANCELADO: 'status-cancelado',
  SAIU: 'status-saiu',
  CHEGOU: 'status-chegou',
}

export const statusOptions: TripStatus[] = [
  'AGENDADO',
  'NO HORARIO',
  'EMBARQUE',
  'ATRASADO',
  'CANCELADO',
  'SAIU',
  'CHEGOU',
]

export const directionOptions: TripDirection[] = ['SAIDA', 'CHEGADA']

export type TripType = 
  'INTERESTADUAL' | 'ESTADUAL' | 'LOCAL' | 'INTERMUNICIPAL' | 'METROPOLITANO'

export const typeOptions: TripType[] = [
  'INTERESTADUAL', 'ESTADUAL', 'LOCAL', 'INTERMUNICIPAL', 'METROPOLITANO'
]

export const parseTime = (time: string) => {
  if (!time) return Number.POSITIVE_INFINITY
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + minutes
}

export const formatTime = (time: string | null | undefined) => time || '-'

export function normalizeTrip(t: Trip): Trip & { trip_direction: TripDirection } {
  // /trips/list pode devolver status e type como objeto {code, value}; converte pra texto
  const rawStatus: unknown = t.status
  const status =
    typeof rawStatus === 'object' && rawStatus !== null
      ? String((rawStatus as { code?: string }).code ?? '')
      : String(rawStatus ?? '')

  const rawType: unknown = t.type
  const type =
    typeof rawType === 'object' && rawType !== null
      ? String((rawType as { code?: string }).code ?? '')
      : String(rawType ?? '')

  return {
    ...t,
    status,
    type,
    trip_direction: (t.trip_direction as TripDirection) || 'SAIDA',
    estimated_time: t.estimated_time ?? null,
  }
}

export function readError(error: unknown, fallback: string) {
  if (error instanceof Error) return error.message
  return fallback
}

export const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })

/** Props que toda aba recebe do App: como avisar o usuário e como recarregar os dados. */
export type AbaProps = {
  showNotification: (kind: Notification['kind'], message: string) => void
  refreshAllAdminData: () => Promise<void>
}
