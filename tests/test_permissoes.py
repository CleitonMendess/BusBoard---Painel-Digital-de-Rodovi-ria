"""Testes de permissão: o que o ADM pode e o que o operador não pode."""
from conftest import criar_usuario, token_de


def test_operador_nao_lista_usuarios(client, auth_operador):
    assert client.get("/auth/users", headers=auth_operador).status_code == 403


def test_operador_nao_cria_adm(client, auth_operador):
    resposta = client.post(
        "/auth/creat_user",
        headers=auth_operador,
        json={
            "name": "Novo",
            "email": "novo@teste.com",
            "password": "senha123",
            "role": "adm",
        },
    )
    assert resposta.status_code == 403
    assert "administradores" in resposta.json()["detail"]


def test_operador_cria_operador(client, auth_operador):
    resposta = client.post(
        "/auth/creat_user",
        headers=auth_operador,
        json={
            "name": "Novo",
            "email": "novo@teste.com",
            "password": "senha123",
            "role": "operador",
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["role"] == "operador"


def test_sem_token_nao_cria_adm(client):
    """Regra de segurança: o primeiro ADM não nasce pela API aberta."""
    resposta = client.post(
        "/auth/creat_user",
        json={
            "name": "Auto",
            "email": "auto@teste.com",
            "password": "senha123",
            "role": "adm",
        },
    )
    assert resposta.status_code == 403


def test_email_duplicado(client, auth_adm):
    corpo = {
        "name": "Repetido",
        "email": "dup@teste.com",
        "password": "senha123",
    }
    assert client.post("/auth/creat_user", headers=auth_adm, json=corpo).status_code == 200
    segunda = client.post("/auth/creat_user", headers=auth_adm, json=corpo)
    assert segunda.status_code == 400


def test_adm_promove_operador(client, auth_adm, session, operador_id):
    from models import User

    resposta = client.patch(
        f"/auth/users/{operador_id}/role",
        headers=auth_adm,
        json={"role": "adm"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["role_atual"] == "adm"
    assert session.get(User, operador_id).role == "adm"


def test_nao_pode_mudar_a_propria_funcao(client, auth_adm, adm_id):
    resposta = client.patch(
        f"/auth/users/{adm_id}/role",
        headers=auth_adm,
        json={"role": "operador"},
    )
    assert resposta.status_code == 400
    assert "própria" in resposta.json()["detail"]


def test_role_desconhecida_recebe_400(client, auth_adm, operador_id):
    resposta = client.patch(
        f"/auth/users/{operador_id}/role",
        headers=auth_adm,
        json={"role": "superusuario"},
    )
    assert resposta.status_code == 400


def test_operador_nao_desativa_usuario(client, auth_operador, adm_id):
    resposta = client.patch(
        f"/auth/users/{adm_id}/active",
        headers=auth_operador,
        json={"active": False},
    )
    assert resposta.status_code == 403


def test_adm_desativa_e_reativa_usuario(client, auth_adm, session, operador_id):
    from models import User

    desativa = client.patch(
        f"/auth/users/{operador_id}/active",
        headers=auth_adm,
        json={"active": False},
    )
    assert desativa.status_code == 200
    assert desativa.json()["active"] is False
    assert session.get(User, operador_id).active is False

    reativa = client.patch(
        f"/auth/users/{operador_id}/active",
        headers=auth_adm,
        json={"active": True},
    )
    assert reativa.status_code == 200
    assert session.get(User, operador_id).active is True


def test_nao_pode_desativar_a_si_mesmo(client, auth_adm, adm_id):
    resposta = client.patch(
        f"/auth/users/{adm_id}/active",
        headers=auth_adm,
        json={"active": False},
    )
    assert resposta.status_code == 400


def test_operador_altera_status_de_viagem(client, auth_operador, session, viagem_criada):
    """Operador pode operar a grade; o bloqueio é só no módulo de administração."""
    resposta = client.patch(
        f"/trips/status/{viagem_criada.id}",
        headers=auth_operador,
        params={"status": "EMBARQUE"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["status_atual"] == "EMBARQUE"


def test_status_invalido_recebe_400(client, auth_adm, viagem_criada):
    resposta = client.patch(
        f"/trips/status/{viagem_criada.id}",
        headers=auth_adm,
        params={"status": "DECOLOU"},
    )
    assert resposta.status_code == 400


def test_viagem_inexistente_recebe_404(client, auth_operador):
    resposta = client.patch(
        "/trips/status/9999",
        headers=auth_operador,
        params={"status": "EMBARQUE"},
    )
    assert resposta.status_code == 404
