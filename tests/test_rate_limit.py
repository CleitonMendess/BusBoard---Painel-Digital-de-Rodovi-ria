"""Trava de tentativas de login: não dá para chutar a senha do ADM em loop."""
import pytest

from conftest import criar_usuario, email_de
import rate_limit


@pytest.fixture(autouse=True)
def trava_limpa():
    rate_limit.zerar()
    yield
    rate_limit.zerar()


@pytest.fixture
def relogio(monkeypatch):
    """Relógio controlado, para testar a janela e o bloqueio sem esperar."""
    momento = {"agora": 1000.0}
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: momento["agora"])
    return momento


def tenta_login(client, email, senha="errada"):
    return client.post("/auth/login", json={"email": email, "password": senha})


def test_login_bloqueia_depois_de_muitas_falhas(client, relogio):
    """A tentativa que estoura o limite ainda leva o erro normal; a seguinte é barrada."""
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)

    for _ in range(rate_limit.MAX_TENTATIVAS):
        assert tenta_login(client, email).status_code == 400

    assert tenta_login(client, email).status_code == 429


def test_bloqueio_traz_retry_after(client, relogio):
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)
    for _ in range(rate_limit.MAX_TENTATIVAS):
        tenta_login(client, email)

    resposta = tenta_login(client, email)
    assert resposta.status_code == 429
    assert int(resposta.headers["retry-after"]) > 0
    assert "Muitas tentativas" in resposta.json()["detail"]


def test_senha_certa_nao_passa_enquanto_esta_bloqueado(client, relogio):
    """O bloqueio vale mesmo com a senha certa: é o que impede o chute."""
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)
    for _ in range(rate_limit.MAX_TENTATIVAS):
        tenta_login(client, email)

    assert tenta_login(client, email, "senha123").status_code == 429


def test_destrava_passado_o_tempo(client, relogio):
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)
    for _ in range(rate_limit.MAX_TENTATIVAS):
        tenta_login(client, email)
    assert tenta_login(client, email).status_code == 429

    relogio["agora"] += rate_limit.BLOQUEIO_SEGUNDOS + 1

    assert tenta_login(client, email, "senha123").status_code == 200


def test_login_certo_limpa_o_historico(client, relogio):
    """Errar, acertar e errar de novo não pode somar no mesmo contador."""
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)

    for _ in range(rate_limit.MAX_TENTATIVAS - 1):
        assert tenta_login(client, email).status_code == 400
    assert tenta_login(client, email, "senha123").status_code == 200

    # errou de novo, mas o contador tinha sido zerado pelo acerto
    assert tenta_login(client, email).status_code == 400


def test_falhas_antigas_somem_da_janela(client, relogio):
    user_id = criar_usuario(role="adm", nome="Alvo")
    email = email_de(user_id)

    for _ in range(rate_limit.MAX_TENTATIVAS - 1):
        tenta_login(client, email)

    # quase estourou a janela: as falhas antigas ainda contam
    relogio["agora"] += rate_limit.JANELA_SEGUNDOS - 1
    assert tenta_login(client, email).status_code == 400
    assert tenta_login(client, email).status_code == 429

    # deu tempo de a janela virar: o contador zera e o login volta a responder
    relogio["agora"] += rate_limit.JANELA_SEGUNDOS
    assert tenta_login(client, email).status_code == 400


def test_outro_email_nao_herda_a_trava(client, relogio):
    alvo = email_de(criar_usuario(role="adm", nome="Alvo"))
    outro = email_de(criar_usuario(role="adm", nome="Outro"))

    for _ in range(rate_limit.MAX_TENTATIVAS):
        tenta_login(client, alvo)

    assert tenta_login(client, alvo).status_code == 429
    assert tenta_login(client, outro, "senha123").status_code == 200


def test_login_form_tambem_e_protegido(client, relogio):
    email = email_de(criar_usuario(role="adm", nome="Alvo"))

    for _ in range(rate_limit.MAX_TENTATIVAS):
        client.post("/auth/login-form", data={"username": email, "password": "errada"})

    resposta = client.post("/auth/login-form", data={"username": email, "password": "senha123"})
    assert resposta.status_code == 429


def test_login_form_normal_continua_funcionando(client):
    email = email_de(criar_usuario(role="adm", nome="Alvo"))
    resposta = client.post("/auth/login-form", data={"username": email, "password": "senha123"})
    assert resposta.status_code == 200
    assert resposta.json()["access_token"]


def test_usuario_inexistente_tambem_conta(client, relogio):
    """Não dá para usar e-mail falso para não contar tentativa."""
    for _ in range(rate_limit.MAX_TENTATIVAS):
        assert tenta_login(client, "fantasma@teste.com").status_code == 400

    assert tenta_login(client, "fantasma@teste.com").status_code == 429
