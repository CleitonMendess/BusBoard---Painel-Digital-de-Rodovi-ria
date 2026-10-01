import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type PendenteConfirmacao } from './api'

// De quanto em quanto tempo se pergunta ao servidor se há viagem para conferir.
const INTERVALO_MS = 20_000

/**
 * Viagens cujo horário já passou e que ninguém confirmou ainda.
 *
 * O servidor é quem decide o que está pendente (ele conhece o fuso e o "dia
 * operacional"); aqui só se pergunta de tempos em tempos e se guarda a lista.
 * O mesmo dado serve ao painel do operador e ao do administrador, então os
 * dois veem o mesmo aviso.
 */
export function useAvisosChegada(ativo: boolean) {
  const [pendentes, setPendentes] = useState<PendenteConfirmacao[]>([])
  const timer = useRef<number | null>(null)

  const carregar = useCallback(async () => {
    if (!ativo) {
      setPendentes([])
      return
    }
    try {
      const r = await api.trips.pendentesConfirmacao()
      setPendentes(r.viagens)
    } catch {
      // Uma falha momentânea não pode limpar o aviso que o operador já está vendo;
      // a próxima rodada tenta de novo.
    }
  }, [ativo])

  useEffect(() => {
    if (!ativo) return
    void carregar()
    timer.current = window.setInterval(() => void carregar(), INTERVALO_MS)
    return () => {
      if (timer.current !== null) window.clearInterval(timer.current)
    }
  }, [ativo, carregar])

  return { pendentes, recarregar: carregar }
}

/** Recomeça a contagem das PendenteConfirmacao em [inicio, fim] em ordem. */
export function pendentesOrdenadas(lista: PendenteConfirmacao[]) {
  return [...lista].sort((a, b) => a.scheduled_time.localeCompare(b.scheduled_time))
}