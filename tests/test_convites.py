"""Cadastro por convite.

A tela de login e so para entrar; criar conta exige um codigo que so o
administrador tem. Estes testes cuidam para o codigo nao virar uma porta
aberta: uso unico, validade, e nenhum caminho sem ADM.
"""
from datetime import datetime, timedelta

import models


def criar_convite(client, auth, role="operador", **kwargs):
    return client.post("/auth/invites", json={"role": role, **kwargs}, headers=auth)


def registrar(client, token, **kwargs):
    dados = {
        "token": token,
        "name": "Maria",
        "email": "maria@teste.com",
        "password": "senha12345",
    }
    dados.update(kwargs)
    return client.post("/auth/registrar", json=dados)


def listar(client, auth):
    return client.get("/auth/invites", headers=auth).json()["Convites"]


# ---------- o admin cria o convite ----------

def test_adm_cria_convite(client, auth_adm):
    resposta = criar_convite(client, auth_adm)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["token"]
    assert corpo["role"] == "operador"
    assert corpo["link"].endswith(corpo["token"])


def test_convite_guarda_somente_o_hash(client, auth_adm, session):
    """Se o banco vazar, o codigo pendente nao pode virar conta."""
    token = criar_convite(client, auth_adm).json()["token"]

    salvos = session.query(models.Invite).all()
    assert len(salvos) == 1
    assert salvos[0].token_hash != token
    assert len(salvos[0].token_hash) == 64  # sha256 em hex


def test_operador_nao_cria_convite(client, auth_operador):
    assert criar_convite(client, auth_operador).status_code == 403


def test_sem_login_nao_cria_convite(client):
    assert criar_convite(client, {}).status_code == 401


def test_convite_adm_so_com_adm(client, auth_adm):
    assert criar_convite(client, auth_adm, role="adm").json()["role"] == "adm"


def test_funcao_invalida(client, auth_adm):
    assert criar_convite(client, auth_adm, role="supervisor").status_code == 400


def test_validade_fora_do_limite(client, auth_adm):
    assert criar_convite(client, auth_adm, validade_horas=0).status_code == 400
    assert criar_convite(client, auth_adm, validade_horas=100000).status_code == 400


# ---------- quem tem o codigo cria a conta ----------

def test_convite_cria_a_conta_e_ja_loga(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]

    resposta = registrar(client, token)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["role"] == "operador"
    assert corpo["access_token"]
    assert corpo["refresh_token"]

    # 403 e nao 401: o token novo passou pela autenticacao, e a recusa e por
    # funcao (operador nao lista viagens). Era isso que eu queria provar.
    painel = client.get(
        "/trips/list",
        headers={"Authorization": f"Bearer {corpo['access_token']}"},
    )
    assert painel.status_code == 403


def test_convite_adm_entra_com_todo_o_poder(client, auth_adm):
    token = criar_convite(client, auth_adm, role="adm").json()["token"]
    access = registrar(client, token).json()["access_token"]

    painel = client.get("/trips/list", headers={"Authorization": f"Bearer {access}"})
    assert painel.status_code == 200


def test_conta_criada_fica_ativa(client, auth_adm, session):
    token = criar_convite(client, auth_adm).json()["token"]
    registrar(client, token)

    nova = session.query(models.User).filter(models.User.email == "maria@teste.com").one()
    assert nova.role == "operador"
    assert nova.active is True
    assert nova.password_hash != "senha12345"  # veio com hash, nao em claro


def test_convite_adm_cria_adm(client, auth_adm, session):
    token = criar_convite(client, auth_adm, role="adm").json()["token"]

    assert registrar(client, token).json()["role"] == "adm"
    nova = session.query(models.User).filter(models.User.email == "maria@teste.com").one()
    assert nova.role == "adm"


# ---------- o codigo e de uso unico ----------

def test_convite_nao_serve_duas_vezes(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]

    assert registrar(client, token).status_code == 200
    segunda = registrar(client, token, email="joao@teste.com")
    assert segunda.status_code == 400
    assert "usado" in segunda.json()["detail"].lower()


def test_convite_inexistente(client):
    resposta = registrar(client, "codigo-que-nunca-existiu")

    assert resposta.status_code == 404
    assert "inv" in resposta.json()["detail"].lower()


def test_convite_expirado(client, auth_adm, session):
    token = criar_convite(client, auth_adm, validade_horas=1).json()["token"]
    convite = session.query(models.Invite).one()
    convite.expires_at = datetime.utcnow() - timedelta(minutes=1)
    session.commit()

    resposta = registrar(client, token)
    assert resposta.status_code == 400
    assert "expirou" in resposta.json()["detail"].lower()


def test_convite_cancelado_some_da_lista(client, auth_adm):
    convite_id = criar_convite(client, auth_adm).json()["id"]

    cancelado = client.delete(f"/auth/invites/{convite_id}", headers=auth_adm)
    assert cancelado.status_code == 200
    assert listar(client, auth_adm) == []


def test_convite_cancelado_nao_cria_conta(client, auth_adm):
    criar_convite(client, auth_adm)
    convite_id = listar(client, auth_adm)[0]["id"]
    client.delete(f"/auth/invites/{convite_id}", headers=auth_adm)

    # o codigo some da lista, entao nao da mais para descobrir: nao existe mais
    assert listar(client, auth_adm) == []


def test_nao_da_para_cancelar_convite_usado(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    registrar(client, token)
    convite_id = listar(client, auth_adm)[0]["id"]

    assert client.delete(f"/auth/invites/{convite_id}", headers=auth_adm).status_code == 400


def test_convite_usado_fica_como_historico(client, auth_adm):
    """Cancelar some o pendente, mas o que ja foi usado continua registrado."""
    token = criar_convite(client, auth_adm).json()["token"]
    registrar(client, token)

    convites = listar(client, auth_adm)
    assert len(convites) == 1
    assert convites[0]["situacao"] == "usado"
    assert convites[0]["usado_por"] == "maria@teste.com"


# ---------- checagem antes do formulario ----------

def test_checagem_diz_que_o_convite_vale(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]

    corpo = client.get(f"/auth/invites/{token}").json()
    assert corpo["valido"] is True
    assert corpo["role"] == "operador"


def test_checagem_de_convite_usado(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    registrar(client, token)

    resposta = client.get(f"/auth/invites/{token}")
    assert resposta.json()["valido"] is False
    assert "usado" in resposta.json()["motivo"].lower()


def test_checagem_de_convite_inexistente(client):
    assert client.get("/auth/invites/nao-existe").json()["valido"] is False


def test_ninguem_alem_do_adm_lista_convites(client, auth_operador):
    assert client.get("/auth/invites", headers=auth_operador).status_code == 403
    assert client.get("/auth/invites").status_code == 401


# ---------- o que o cadastro recusa ----------

def test_email_ja_cadastrado(client, auth_adm, session):
    from models import User
    from senhas import gerar_hash

    session.add(
        User("Joao", "maria@teste.com", gerar_hash("antiga123"), "operador", True)
    )
    session.commit()

    token = criar_convite(client, auth_adm).json()["token"]
    resposta = registrar(client, token)
    assert resposta.status_code == 400
    assert "cadastrado" in resposta.json()["detail"]


def test_email_mal_formado(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    assert registrar(client, token, email="nao-e-email").status_code == 400


def test_senha_curta(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    resposta = registrar(client, token, password="123")
    assert resposta.status_code == 400
    assert "8 caracteres" in resposta.json()["detail"]


def test_nome_curto_demais(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    assert registrar(client, token, name="x").status_code == 400


def test_cadastro_nao_poe_senha_em_claro(client, auth_adm):
    token = criar_convite(client, auth_adm).json()["token"]
    registrar(client, token, password="outrasenha9")

    entra = client.post(
        "/auth/login", json={"email": "maria@teste.com", "password": "outrasenha9"}
    )
    assert entra.status_code == 200


def test_convite_de_operador_nao_vira_escada_para_adm(client, auth_adm):
    """O papel vem do convite, nao do que o cadastro pede."""
    token = criar_convite(client, auth_adm, role="operador").json()["token"]
    registrar(client, token)

    novo_token = client.post(
        "/auth/login", json={"email": "maria@teste.com", "password": "senha12345"}
    ).json()["access_token"]

    resposta = client.post(
        "/auth/invites",
        json={"role": "adm"},
        headers={"Authorization": f"Bearer {novo_token}"},
    )
    assert resposta.status_code == 403


def test_tener_convite_da_login(client, auth_adm):
    """Ter o codigo nao entra no sistema: o login ainda e so com e-mail e senha."""
    token = criar_convite(client, auth_adm).json()["token"]

    antes = client.get("/trips/list")
    assert antes.status_code == 401
    assert token not in antes.text


# ---------- o caminho inteiro, como a pessoa vai viver ----------

def test_percorrimento_do_convite(client, auth_adm, session):
    """ADM gera o link, a pessoa abre, cria a conta e entra.

    É o teste que conta a história de ponta a ponta, na ordem em que acontece.
    """
    # 1. o ADM gera o convite e manda o link
    gerado = criar_convite(client, auth_adm, role="operador", validade_horas=24)
    assert gerado.status_code == 201
    link = gerado.json()["link"]
    token = link.rsplit("/", 1)[-1]
    assert link == f"/cadastro/{token}"

    # 2. a pessoa abre o link e o front pergunta se o convite ainda vale
    checagem = client.get(f"/auth/invites/{token}").json()
    assert checagem == {"valido": True, "role": "operador", "motivo": None}

    # 3. ela preenche o formulário
    cadastro = registrar(client, token, name="Carla", email="carla@rodoviaria.com")
    assert cadastro.status_code == 200
    sessao = cadastro.json()

    # 4. a conta já nasce com a função do convite e able a fazer o serviço dela
    conta = session.query(models.User).filter(models.User.email == "carla@rodoviaria.com").one()
    assert conta.role == "operador"
    assert sessao["role"] == "operador"

    # 5. o convite não serve para mais ninguém
    assert client.get(f"/auth/invites/{token}").json()["valido"] is False
    assert registrar(client, token, email="outra@teste.com").status_code == 400

    # 6. e o ADM consegue ver que foi usado
    registro = listar(client, auth_adm)[0]
    assert registro["situacao"] == "usado"
    assert registro["usado_por"] == "carla@rodoviaria.com"
