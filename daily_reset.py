# daily_reset.py → reinício diário da grade de viagens
#
# As viagens da rodoviária se repetem todo dia. Este módulo devolve todas as viagens
# para AGENDADO (e apaga a previsão de horário) uma vez por dia, de madrugada,
# para que o painel comece o dia limpo sem ninguém precisar mexer.
#
# Configuração opcional no .env:
#   DAILY_RESET_HOUR=3            hora do reinício (0-23). Padrão: 3
#   TZ_NAME=America/Sao_Paulo     fuso horário. Padrão: Brasília (UTC-3)
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from models import db, Trip, AppState, StatusLog

log = logging.getLogger("busboard.reset")

# uma cópia do banco por dia, logo depois de virar o dia. Vem depois do import
# para não puxar o sqlite3 no caminho do primeiro admin (criar_admin.py).
from backup import criar_backup  # noqa: E402

RESET_HOUR = int(os.getenv("DAILY_RESET_HOUR", "3"))
TZ_NAME = os.getenv("TZ_NAME", "America/Sao_Paulo")
CHAVE_ULTIMO_DIA = "last_reset_day"

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo(TZ_NAME)
except Exception:  # sem base de fusos (comum no Windows): o Brasil hoje é UTC-3 fixo
    LOCAL_TZ = timezone(timedelta(hours=-3))

SessionLocal = sessionmaker(bind=db)


def dia_operacional(agora: datetime | None = None) -> str:
    """O "dia" da rodoviária começa na hora do reinício, não à meia-noite."""
    momento = agora if agora is not None else datetime.now(LOCAL_TZ)
    return (momento - timedelta(hours=RESET_HOUR)).date().isoformat()


def reiniciar_viagens(session) -> int:
    """Volta todas as viagens para AGENDADO e limpa a previsão. Devolve quantas foram."""
    viagens = session.query(Trip).all()
    for viagem in viagens:
        viagem.status = "AGENDADO"
        viagem.estimated_time = None
    _gravar_dia(session, dia_operacional())
    session.commit()
    return len(viagens)


# Uma viagem só vira ATRASADO por decisão de quem opera: o sistema pergunta se o
# ônibus chegou e só marca atrasada quando a resposta é não (ver OperatorPanel).
# Marcar sozinho fazia a TV mostrar atraso sem ninguém ter visto o ônibus, então
# não existe mais tarefa de fundo que altere status por conta própria.
STATUS_QUE_PEDEM_CONFIRMACAO = ("AGENDADO", "NO HORARIO", "EMBARQUE")


def _gravar_dia(session, dia: str):
    estado = session.get(AppState, CHAVE_ULTIMO_DIA)
    if estado is None:
        session.add(AppState(CHAVE_ULTIMO_DIA, dia))
    else:
        estado.value = dia


def executar_reinicio_se_preciso() -> bool:
    """Reinicia a grade se ainda não foi reiniciada no dia operacional de hoje."""
    hoje = dia_operacional()
    with SessionLocal() as session:
        estado = session.get(AppState, CHAVE_ULTIMO_DIA)
        if estado is None:
            # primeira vez que o sistema roda com este recurso: só marca o dia, não apaga nada
            _gravar_dia(session, hoje)
            session.commit()
            return False
        if estado.value == hoje:
            return False
        total = reiniciar_viagens(session)
        log.info("Reinício diário: %s viagens voltaram para AGENDADO", total)
        _backup_do_dia()
        return True


def _backup_do_dia() -> None:
    """Copia o banco logo após virar o dia. Falha aqui não pode derrubar o reset."""
    try:
        criar_backup()
    except Exception:
        log.exception("Não consegui fazer o backup diário (o reinício em si já foi feito)")


async def rodar_reinicio_diario():
    """Tarefa de fundo: confere a cada minuto. Se o servidor ficou desligado de madrugada,
    o reinício acontece assim que ele voltar."""
    while True:
        try:
            await asyncio.to_thread(executar_reinicio_se_preciso)
        except Exception:
            log.exception("Falha no reinício diário")
        await asyncio.sleep(60)


def _horario_de(viagem, dia: datetime) -> datetime | None:
    """Momento scheduled_time da viagem no dia de referência, ou None se for lixo."""
    try:
        h, m = map(int, viagem.scheduled_time.split(":")[:2])
        return dia.replace(hour=h, minute=m, second=0, microsecond=0)
    except (AttributeError, ValueError):
        return None


def _previsao_de(viagem, dia: datetime) -> datetime | None:
    """Momento estimated_time da viagem no dia de referência, ou None se não houver/lixo."""
    if not viagem.estimated_time:
        return None
    try:
        h, m = map(int, viagem.estimated_time.split(":")[:2])
        return dia.replace(hour=h, minute=m, second=0, microsecond=0)
    except (AttributeError, ValueError):
        return None


def viagens_para_confirmar(session, agora: datetime | None = None) -> list[Trip]:
    """Viagens que já deveriam ter saído/chegado e que ninguém tocou desde o horário/previsão.

    Entra aqui toda viagem cujo horário (scheduled_time) ou previsão (estimated_time) já passou
    e segue num status em que ainda dá para dizer se o ônibus chegou. Não mexe no banco: só lê.

    Quem já mexeu na viagem depois do horário/previsão não entra mais na lista: é o que
    faz o aviso sumir depois de "Chegou" ou "Não chegou", sem precisar guardar
    um campo novo no banco. O StatusLog já conta essa história.
    """
    momento = agora if agora is not None else datetime.now(LOCAL_TZ)
    inicio_do_dia = momento.replace(hour=0, minute=0, second=0, microsecond=0)

    # Os logs de status são gravados em UTC sem tzinfo, então a comparação
    # também é feita em UTC. Guardamos o último momento em que cada viagem teve
    # o status mexido.
    dia_em_utc = inicio_do_dia.astimezone(timezone.utc).replace(tzinfo=None)
    mexidas_em: dict[int, datetime] = {}
    for log in session.query(StatusLog).filter(StatusLog.changed_at >= dia_em_utc).all():
        anterior = mexidas_em.get(log.trip_id)
        if anterior is None or log.changed_at > anterior:
            mexidas_em[log.trip_id] = log.changed_at

    pendentes = []
    for viagem in session.query(Trip).all():
        if str(viagem.status) not in STATUS_QUE_PEDEM_CONFIRMACAO:
            continue

        # Verifica scheduled_time
        horario = _horario_de(viagem, inicio_do_dia)
        horario_passou = horario is not None and momento >= horario
        horario_ja_tratado = horario is not None and mexidas_em.get(viagem.id, datetime.min) >= horario.astimezone(timezone.utc).replace(tzinfo=None)

        # Verifica estimated_time (previsão)
        previsao = _previsao_de(viagem, inicio_do_dia)
        previsao_passou = previsao is not None and momento >= previsao
        previsao_ja_tratada = previsao is not None and mexidas_em.get(viagem.id, datetime.min) >= previsao.astimezone(timezone.utc).replace(tzinfo=None)

        # Se nenhum dos dois passou, não está pendente
        if not horario_passou and not previsao_passou:
            continue

        # Se ambos passaram mas ambos já foram tratados, não está pendente
        if horario_passou and previsao_passou and horario_ja_tratado and previsao_ja_tratada:
            continue
        if horario_passou and not previsao_passou and horario_ja_tratado:
            continue
        if previsao_passou and not horario_passou and previsao_ja_tratada:
            continue

        pendentes.append(viagem)
    return sorted(pendentes, key=lambda v: v.scheduled_time)
