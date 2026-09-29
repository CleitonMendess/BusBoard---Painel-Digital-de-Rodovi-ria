"""Reinício diário da grade de viagens (daily_reset)."""
from datetime import datetime

import daily_reset
from models import AppState, Trip


def marcar_dia(session, dia):
    estado = session.get(AppState, daily_reset.CHAVE_ULTIMO_DIA)
    if estado is None:
        session.add(AppState(daily_reset.CHAVE_ULTIMO_DIA, dia))
    else:
        estado.value = dia
    session.commit()


def test_dia_operacional_comeca_na_hora_do_reinicio(monkeypatch):
    """Às 02h ainda é o dia anterior: a madrugada pertence à noite anterior."""
    monkeypatch.setattr(daily_reset, "RESET_HOUR", 3)

    assert daily_reset.dia_operacional(datetime(2026, 9, 29, 2, 30)) == "2026-09-28"
    assert daily_reset.dia_operacional(datetime(2026, 9, 29, 3, 0)) == "2026-09-29"
    assert daily_reset.dia_operacional(datetime(2026, 9, 29, 23, 59)) == "2026-09-29"


def test_dia_operacional_muda_meia_noite(monkeypatch):
    monkeypatch.setattr(daily_reset, "RESET_HOUR", 0)
    assert daily_reset.dia_operacional(datetime(2026, 9, 29, 0, 0)) == "2026-09-29"
    assert daily_reset.dia_operacional(datetime(2026, 9, 30, 0, 0)) == "2026-09-30"


def test_primeira_execucao_apenas_marca_o_dia(session, viagem_criada):
    """Se o recurso entra no ar no meio do dia, não pode apagar a grade."""
    viagem_criada.status = "EMBARQUE"
    session.commit()

    assert daily_reset.executar_reinicio_se_preciso() is False
    session.expire_all()
    assert session.get(Trip, viagem_criada.id).status == "EMBARQUE"
    assert session.get(AppState, daily_reset.CHAVE_ULTIMO_DIA) is not None


def test_reinicia_quando_o_dia_mudou(session, viagem_criada):
    viagem_criada.status = "CHEGOU"
    viagem_criada.estimated_time = "14:30"
    session.commit()

    marcar_dia(session, "2000-01-01")

    assert daily_reset.executar_reinicio_se_preciso() is True

    session.expire_all()
    viagem = session.get(Trip, viagem_criada.id)
    assert viagem.status == "AGENDADO"
    assert viagem.estimated_time is None
    assert session.get(AppState, daily_reset.CHAVE_ULTIMO_DIA).value == daily_reset.dia_operacional()


def test_nao_reinicia_duas_vezes_no_mesmo_dia(session, viagem_criada):
    marcar_dia(session, daily_reset.dia_operacional())
    viagem_criada.status = "ATRASADO"
    session.commit()

    assert daily_reset.executar_reinicio_se_preciso() is False
    session.expire_all()
    assert session.get(Trip, viagem_criada.id).status == "ATRASADO"


def test_reinicia_todas_as_viagens(session, viagem_criada):
    segunda = Trip(
        type="LOCAL",
        scheduled_time="22:00",
        company_id=viagem_criada.company_id,
        destination_id=viagem_criada.destination_id,
        platform_id=viagem_criada.platform_id,
        trip_direction="CHEGADA",
        status="CANCELADO",
    )
    session.add(segunda)
    session.commit()

    marcar_dia(session, "2000-01-01")
    assert daily_reset.reiniciar_viagens(session) == 2

    session.expire_all()
    assert {v.status for v in session.query(Trip).all()} == {"AGENDADO"}
