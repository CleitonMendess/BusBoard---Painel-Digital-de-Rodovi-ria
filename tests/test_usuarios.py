"""Exclusão de usuários e de viagens, e o que precisa acontecer junto."""
from conftest import token_de


def registrar_status(client, auth, viagem_id, status="EMBARQUE"):
    return client.patch(
        f"/trips/status/{viagem_id}",
        headers=auth,
        params={"status": status},
    )


def test_adm_exclui_usuario(client, auth_adm, operador_id, outra_sessao):
    from models import User

    resposta = client.delete(f"/auth/users/{operador_id}", headers=auth_adm)
    assert resposta.status_code == 200
    assert "excluído" in resposta.json()["mensagem"]
    assert outra_sessao.get(User, operador_id) is None


def test_historico_de_status_e_preservado(client, auth_adm, operador_id, viagem_criada, session, outra_sessao):
    """O log da viagem continua existindo, só perde o nome de quem mudou."""
    from models import StatusLog

    assert registrar_status(client, auth_adm, viagem_criada.id, "EMBARQUE").status_code == 200
    assert session.query(StatusLog).filter(StatusLog.changed_by == operador_id).count() == 0

    headers_operador = {"Authorization": f"Bearer {token_de(operador_id)}"}
    assert registrar_status(client, headers_operador, viagem_criada.id, "ATRASADO").status_code == 200

    assert client.delete(f"/auth/users/{operador_id}", headers=auth_adm).status_code == 200

    logs = {log.new_status: log for log in outra_sessao.query(StatusLog).all()}
    assert len(logs) == 2
    # o log do operador excluído fica sem autor; o do ADM continua com ele
    assert logs["ATRASADO"].changed_by is None
    assert logs["EMBARQUE"].changed_by is not None


def test_nao_exclui_a_si_mesmo(client, auth_adm, adm_id, outra_sessao):
    from models import User

    resposta = client.delete(f"/auth/users/{adm_id}", headers=auth_adm)
    assert resposta.status_code == 400
    assert outra_sessao.get(User, adm_id) is not None


def test_operador_nao_exclui_usuario(client, auth_operador, adm_id, outra_sessao):
    from models import User

    resposta = client.delete(f"/auth/users/{adm_id}", headers=auth_operador)
    assert resposta.status_code == 403
    assert outra_sessao.get(User, adm_id) is not None


def test_excluir_usuario_inexistente(client, auth_adm):
    assert client.delete("/auth/users/9999", headers=auth_adm).status_code == 404


def test_excluir_usuario_sem_token(client, operador_id):
    assert client.delete(f"/auth/users/{operador_id}").status_code == 401


def test_adm_exclui_viagem(client, auth_adm, viagem_criada, outra_sessao):
    from models import Trip

    resposta = client.delete(f"/trips/{viagem_criada.id}", headers=auth_adm)
    assert resposta.status_code == 200
    assert "excluida" in resposta.json()["mensagem"]
    assert outra_sessao.query(Trip).filter(Trip.id == viagem_criada.id).count() == 0


def test_mensagem_de_exclusao_de_viagem_traz_o_nome_da_empresa(client, auth_adm, viagem_criada):
    resposta = client.delete(f"/trips/{viagem_criada.id}", headers=auth_adm)
    assert "Onibus Teste" in resposta.json()["mensagem"]


def test_excluir_viagem_inexistente(client, auth_adm):
    assert client.delete("/trips/9999", headers=auth_adm).status_code == 404


def test_operador_nao_exclui_viagem(client, auth_operador, viagem_criada, outra_sessao):
    from models import Trip

    resposta = client.delete(f"/trips/{viagem_criada.id}", headers=auth_operador)
    assert resposta.status_code == 403
    assert outra_sessao.get(Trip, viagem_criada.id) is not None
