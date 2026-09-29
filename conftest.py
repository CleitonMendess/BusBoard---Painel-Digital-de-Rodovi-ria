"""Configuração dos testes.

O app usa um SQLite fixo (models.db) criado no import. Para os testes, apontamos
esse engine para um banco temporário ANTES de importar o main, assim nenhum
teste encosta no banco de verdade.
"""
import os
import tempfile
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "segredo-apenas-para-teste-com-tamanho-suficiente")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("DAILY_RESET_HOUR", "3")
# os testes não devem escribir no log nem criar backups na pasta do projeto
os.environ.setdefault("LOG_FILE", "")
os.environ.setdefault(
    "BACKUP_PASTA", os.path.join(tempfile.gettempdir(), "busboard_backups_teste")
)

import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ARQUIVO_BANCO_TESTE = os.path.join(tempfile.gettempdir(), "busboard_teste.db")
if os.path.exists(ARQUIVO_BANCO_TESTE):
    os.remove(ARQUIVO_BANCO_TESTE)

# Banco em arquivo temporário: cada sessão abre sua própria conexão, como em produção.
engine_teste = create_engine(
    f"sqlite:///{ARQUIVO_BANCO_TESTE}",
    connect_args={"check_same_thread": False},
)
models.db = engine_teste
models.Base.metadata.create_all(bind=engine_teste)

SessionTeste = sessionmaker(bind=engine_teste, expire_on_commit=False)

import daily_reset  # noqa: E402  (precisa importar depois do patch)
from main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def banco_limpo():
    """Zera as tabelas antes de cada teste."""
    with SessionTeste() as session:
        for tabela in reversed(models.Base.metadata.sorted_tables):
            session.execute(tabela.delete())
        session.commit()
    daily_reset.SessionLocal = SessionTeste
    return


@pytest.fixture
def client():
    # sem lifespan: não sobe a tarefa de reinício diário de fundo
    return TestClient(app)


@pytest.fixture
def session():
    with SessionTeste() as s:
        yield s


@pytest.fixture
def outra_sessao():
    """Sessão limpa, sem o cache de objetos: use para conferir o que o app gravou."""
    with SessionTeste() as s:
        yield s


def email_de(user_id):
    with SessionTeste() as s:
        return s.get(models.User, user_id).email


def criar_usuario(role="operador", active=True, email=None, nome="Teste", senha="senha123"):
    """Cria um usuário direto no banco (evita o custo de hash a cada teste)."""
    from senhas import gerar_hash

    with SessionTeste() as s:
        usuario = models.User(
            nome,
            email or f"{role}-{uuid4().hex[:8]}@teste.com",
            gerar_hash(senha),
            role,
            active,
        )
        s.add(usuario)
        s.commit()
        s.refresh(usuario)
        return usuario.id


@pytest.fixture
def adm_id():
    return criar_usuario(role="adm", nome="Chefe")


@pytest.fixture
def operador_id():
    return criar_usuario(role="operador", nome="Operario")


def token_de(user_id):
    from routes.auth import create_token

    return create_token(user_id)


def refresh_token_de(user_id):
    from datetime import timedelta

    from routes.auth import create_token

    return create_token(user_id, duracao_token=timedelta(days=7))


@pytest.fixture
def viagem_criada(session):
    """Uma viagem de saída completa (empresa, destino, plataforma)."""
    from models import Company, Destination, Platform, Trip

    empresa = Company("Onibus Teste")
    destino = Destination("Cidade Teste", "SP")
    plataforma = Platform(1)
    session.add_all([empresa, destino, plataforma])
    session.commit()

    viagem = Trip(
        type="INTERESTADUAL",
        scheduled_time="10:00",
        company_id=empresa.id,
        destination_id=destino.id,
        platform_id=plataforma.id,
        trip_direction="SAIDA",
    )
    session.add(viagem)
    session.commit()
    session.refresh(viagem)
    return viagem


@pytest.fixture
def auth_adm(adm_id):
    return {"Authorization": f"Bearer {token_de(adm_id)}"}


@pytest.fixture
def auth_operador(operador_id):
    return {"Authorization": f"Bearer {token_de(operador_id)}"}
