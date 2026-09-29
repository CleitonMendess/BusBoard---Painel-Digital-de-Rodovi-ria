"""Serviço do front pelo backend (/, /painel, /assets) e o /health."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main

ARQUIVOS_ESPERADOS = "console.log('oi')"


@pytest.fixture
def dist_falso(tmp_path):
    """Um 'build' na medida, para o teste não depender do npm run build."""
    pasta = tmp_path / "dist"
    (pasta / "assets").mkdir(parents=True)
    (pasta / "index.html").write_text(
        "<!doctype html><html><head><title>BusBoard</title></head><body><div id=root></div></body></html>",
        encoding="utf-8",
    )
    (pasta / "assets" / "index-abc123.js").write_text(ARQUIVOS_ESPERADOS, encoding="utf-8")
    (pasta / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return pasta


@pytest.fixture
def cliente_front(dist_falso):
    app = FastAPI()
    assert main.montar_front(app, dist_falso) is True
    return TestClient(app)


def test_raiz_entrega_o_painel(cliente_front):
    resposta = cliente_front.get("/")

    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert '<div id=root>' in resposta.text


def test_painel_da_tv_usa_o_mesmo_html(cliente_front):
    """O /painel é a TV; o próprio front decide isso pelo caminho."""
    assert cliente_front.get("/painel").text == cliente_front.get("/").text


def test_assets_sao_servidos_com_cache_longo(cliente_front):
    """O nome tem hash: se o conteúdo muda, o nome muda também."""
    resposta = cliente_front.get("/assets/index-abc123.js")

    assert resposta.status_code == 200
    assert resposta.text == ARQUIVOS_ESPERADOS
    assert "immutable" in resposta.headers["cache-control"]


def test_index_nao_fica_cacheado(cliente_front):
    """Senão um deploy novo continua servindo o index antigo."""
    assert "no-cache" in cliente_front.get("/").headers["cache-control"]


def test_arquivos_soltos_do_dist(cliente_front):
    assert cliente_front.get("/favicon.svg").status_code == 200


def test_sem_build_avisa_e_nao_quebra_a_api(tmp_path):
    """Desenvolver sem compilar o front tem que continuar funcionando."""
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    assert main.montar_front(app, tmp_path / "nao-existe") is False

    cliente = TestClient(app)
    assert cliente.get("/health").json() == {"status": "ok"}


def test_health_responde_sem_senha(client):
    """O supervisor precisa checar de fora; não pode pedir token."""
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
