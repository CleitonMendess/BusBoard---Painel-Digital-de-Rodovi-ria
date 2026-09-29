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

from models import db, Trip, AppState

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
