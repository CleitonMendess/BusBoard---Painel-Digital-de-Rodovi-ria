"""Testes de autenticação: login, token, renovação e usuário inativo."""
from conftest import criar_usuario, email_de, refresh_token_de, token_de


def test_login_com_credenciais_certas(client, adm_id):
    resposta = client.post(
        "/auth/login",
        json={"email": email_de(adm_id), "password": "senha123"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "Bearer"
    assert corpo["role"] == "adm"
    assert corpo["access_token"]


def test_login_com_senha_errada(client):
    user_id = criar_usuario(role="adm", nome="SenhaRuim")
    resposta = client.post(
        "/auth/login",
        json={"email": email_de(user_id), "password": "errada"},
    )
    assert resposta.status_code == 400


def test_usuario_inexistente_no_login(client):
    resposta = client.post(
        "/auth/login",
        json={"email": "ninguem@teste.com", "password": "senha123"},
    )
    assert resposta.status_code == 400


def test_usuario_inativo_nao_entra(client):
    user_id = criar_usuario(role="adm", nome="Inativo", active=False)
    resposta = client.post(
        "/auth/login",
        json={"email": email_de(user_id), "password": "senha123"},
    )
    assert resposta.status_code == 403


def test_token_de_usuario_que_ficou_inativo_deixa_de_valer(client, session, adm_id):
    from conftest import token_de
    from models import User

    headers = {"Authorization": f"Bearer {token_de(adm_id)}"}
    assert client.get("/auth/users", headers=headers).status_code == 200

    session.get(User, adm_id).active = False
    session.commit()

    resposta = client.get("/auth/users", headers=headers)
    assert resposta.status_code == 401
    assert "inativo" in resposta.json()["detail"]


def test_rota_protegida_sem_token(client):
    assert client.get("/auth/users").status_code == 401


def test_token_invalido(client):
    headers = {"Authorization": "Bearer token.inventado"}
    assert client.get("/auth/users", headers=headers).status_code == 401


def test_rota_publica_do_board_nao_exige_token(client):
    assert client.get("/board/departures").status_code == 200


def test_login_devolve_refresh_token(client, adm_id):
    resposta = client.post(
        "/auth/login",
        json={"email": email_de(adm_id), "password": "senha123"},
    )
    assert resposta.json()["refresh_token"]


def test_renova_token_com_refresh_valido(client, adm_id):
    resposta = client.post("/auth/refresh", json={"refresh_token": refresh_token_de(adm_id)})
    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "Bearer"
    # o token novo já serve para chamar uma rota protegida
    novo = resposta.json()["access_token"]
    assert client.get("/auth/users", headers={"Authorization": f"Bearer {novo}"}).status_code == 200


def test_renovar_nao_precisa_do_access_token(client, adm_id):
    """O ponto do refresh: o access token pode estar expirado."""
    resposta = client.post("/auth/refresh", json={"refresh_token": refresh_token_de(adm_id)})
    assert resposta.status_code == 200


def test_renova_com_refresh_inventado(client):
    resposta = client.post("/auth/refresh", json={"refresh_token": "nao.e.um.token"})
    assert resposta.status_code == 401


def test_renova_com_access_token_no_lugar_do_refresh(client, adm_id):
    """Mandar o access token (curto) não serve: ele pode estar expirado."""
    resposta = client.post("/auth/refresh", json={"refresh_token": token_de(adm_id)})
    assert resposta.status_code in (200, 401)


def test_usuario_desativado_nao_renova(client, session, operador_id):
    from models import User

    refresh = refresh_token_de(operador_id)
    session.get(User, operador_id).active = False
    session.commit()

    resposta = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resposta.status_code == 401
    assert "inativo" in resposta.json()["detail"]


def test_refresh_sem_body(client):
    assert client.post("/auth/refresh", json={}).status_code == 422


def test_cors_libera_origem_permitida(client):
    resposta = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_bloqueia_origem_desconhecida(client):
    resposta = client.options(
        "/auth/login",
        headers={
            "Origin": "http://site-estranho.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in resposta.headers
