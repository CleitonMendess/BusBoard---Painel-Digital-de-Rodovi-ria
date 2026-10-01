"""Reinício diário da grade de viagens (daily_reset)."""
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import backup
import daily_reset
from models import AppState, StatusLog, Trip


@pytest.fixture
def pasta_backups(tmp_path):
    """Pasta isolada para o backup do teste, sem encostar na pasta de verdade."""
    pasta = tmp_path / "backups"
    pasta.mkdir()
    return pasta


def marcar_dia(session, dia):
    estado = session.get(AppState, daily_reset.CHAVE_ULTIMO_DIA)
    if estado is None:
        session.add(AppState(daily_reset.CHAVE_ULTIMO_DIA, dia))
    else:
        estado.value = dia
    session.commit()


def test_viagem_que_passou_hora_entra_na_confirmacao(session, viagem_criada):
    """A viagem vencida fica esperando resposta; a que ainda vai, não."""
    agora = datetime(2026, 9, 29, 14, 10)
    viagem_criada.scheduled_time = "14:00"
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, agora)

    assert [v.id for v in pendentes] == [viagem_criada.id]


def test_viagem_futura_nao_entra_na_confirmacao(session, viagem_criada):
    viagem_criada.scheduled_time = "18:00"
    session.commit()

    assert daily_reset.viagens_para_confirmar(session, datetime(2026, 9, 29, 14, 10)) == []


def test_viagem_encerrada_nao_entra_na_confirmacao(session, viagem_criada):
    """Quem já confirmou não continua sendo lembrado a cada 20 segundos."""
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.status = "SAIU"
    session.commit()

    assert daily_reset.viagens_para_confirmar(session, datetime(2026, 9, 29, 14, 10)) == []


def test_confirmacao_considera_chegada_e_saida(session, viagem_criada):
    """Chegada também precisa de confirmação: o ônibus esperando é o mesmo problema."""
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.trip_direction = "CHEGADA"
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, datetime(2026, 9, 29, 14, 10))

    assert [v.id for v in pendentes] == [viagem_criada.id]


def test_respondeu_chegou_o_aviso_some(session, viagem_criada):
    """"Chegou" grava NO HORARIO, que está na lista de pendentes. O que tira a viagem
    de lá é ter mexido nela depois do horário, e é isso que o teste mede."""
    agora = datetime(2026, 9, 29, 14, 10)
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.status = "NO HORARIO"
    session.add(
        StatusLog(
            trip_id=viagem_criada.id,
            old_status="AGENDADO",
            new_status="NO HORARIO",
            changed_at=(agora - timedelta(minutes=5)).astimezone(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()

    assert daily_reset.viagens_para_confirmar(session, agora) == []


def test_respondeu_nao_chegou_o_aviso_some(session, viagem_criada):
    agora = datetime(2026, 9, 29, 14, 10)
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.status = "ATRASADO"
    session.add(
        StatusLog(
            trip_id=viagem_criada.id,
            old_status="AGENDADO",
            new_status="ATRASADO",
            changed_at=(agora - timedelta(minutes=2)).astimezone(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()

    assert daily_reset.viagens_para_confirmar(session, agora) == []


def test_mexer_antes_do_horario_nao_tira_o_aviso(session, viagem_criada):
    """Ajuste feito às 13h para uma viagem das 14h não conta como resposta."""
    agora = datetime(2026, 9, 29, 14, 10)
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.status = "NO HORARIO"
    session.add(
        StatusLog(
            trip_id=viagem_criada.id,
            old_status="AGENDADO",
            new_status="NO HORARIO",
            changed_at=datetime(2026, 9, 29, 13, 0).astimezone(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, agora)

    assert [v.id for v in pendentes] == [viagem_criada.id]


def test_mexer_em_outra_viagem_nao_tira_o_aviso(session, viagem_criada):
    """O registro é por viagem: responder uma não responde a outra."""
    agora = datetime(2026, 9, 29, 14, 10)
    viagem_criada.scheduled_time = "14:00"
    outra = Trip(
        type="LOCAL",
        scheduled_time="14:00",
        company_id=viagem_criada.company_id,
        destination_id=viagem_criada.destination_id,
        platform_id=viagem_criada.platform_id,
        trip_direction="SAIDA",
    )
    session.add(outra)
    session.commit()
    session.add(
        StatusLog(
            trip_id=outra.id,
            old_status="AGENDADO",
            new_status="NO HORARIO",
            changed_at=(agora - timedelta(minutes=3)).astimezone(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, agora)

    assert [v.id for v in pendentes] == [viagem_criada.id]


def test_horario_invalido_nao_derruba_a_confirmacao(session, viagem_criada):
    """Um horário quebrado é pulado, não pode estourar a tela de quem opera."""
    viagem_criada.scheduled_time = "14:00"
    quebrada = Trip(
        type="LOCAL",
        scheduled_time="nao-e-hora",
        company_id=viagem_criada.company_id,
        destination_id=viagem_criada.destination_id,
        platform_id=viagem_criada.platform_id,
        trip_direction="SAIDA",
    )
    session.add(quebrada)
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, datetime(2026, 9, 29, 14, 10))

    assert [v.id for v in pendentes] == [viagem_criada.id]


def test_confirmacao_ordena_por_horario(session, viagem_criada):
    agora = datetime(2026, 9, 29, 20, 0)
    viagem_criada.scheduled_time = "11:00"
    session.commit()
    for horario in ("18:00", "13:00"):
        session.add(
            Trip(
                type="LOCAL",
                scheduled_time=horario,
                company_id=viagem_criada.company_id,
                destination_id=viagem_criada.destination_id,
                platform_id=viagem_criada.platform_id,
                trip_direction="SAIDA",
            )
        )
    session.commit()

    pendentes = daily_reset.viagens_para_confirmar(session, agora)

    assert [v.scheduled_time for v in pendentes] == ["11:00", "13:00", "18:00"]


def test_sistema_nao_marca_atrasado_sozinho(session, viagem_criada):
    """Nenhuma função de fundo mexe no status: atrasar é decisão de quem opera."""
    viagem_criada.scheduled_time = "14:00"
    viagem_criada.status = "AGENDADO"
    session.commit()

    antes = str(session.get(Trip, viagem_criada.id).status)
    daily_reset.viagens_para_confirmar(session, datetime(2026, 9, 29, 14, 10))
    session.expire_all()

    assert str(session.get(Trip, viagem_criada.id).status) == antes == "AGENDADO"


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


def test_reinicio_faz_o_backup_do_dia(session, viagem_criada, pasta_backups, monkeypatch):
    """Virar o dia tira uma cópia do banco: é o retrato de como o dia fechou."""
    monkeypatch.setattr(backup, "PASTA_PADRAO", str(pasta_backups))
    viagem_criada.status = "CHEGOU"
    session.commit()
    marcar_dia(session, "2000-01-01")

    assert daily_reset.executar_reinicio_se_preciso() is True

    copias = list(pasta_backups.glob("banco-*.db"))
    assert len(copias) == 1
    with sqlite3.connect(copias[0]) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_falho_nao_derruba_o_reinicio(session, viagem_criada, monkeypatch, caplog):
    """O reset já foi feito; se a cópia falhar, o log explica e o app continua."""
    def falhar(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(daily_reset, "criar_backup", falhar)
    viagem_criada.status = "CHEGOU"
    session.commit()
    marcar_dia(session, "2000-01-01")

    with caplog.at_level(logging.ERROR):
        assert daily_reset.executar_reinicio_se_preciso() is True

    session.expire_all()
    assert session.get(Trip, viagem_criada.id).status == "AGENDADO"
    assert "backup diário" in caplog.text


def test_sem_reinicio_nao_ha_backup(session, viagem_criada, pasta_backups, monkeypatch):
    """Backup a mais toparia encher o disco à toa: só copia quando vira o dia."""
    monkeypatch.setattr(backup, "PASTA_PADRAO", str(pasta_backups))
    marcar_dia(session, daily_reset.dia_operacional())

    assert daily_reset.executar_reinicio_se_preciso() is False
    assert list(pasta_backups.glob("banco-*.db")) == []
