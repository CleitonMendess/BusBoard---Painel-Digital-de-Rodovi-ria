"""A migration do Alembic precisa produzir exatamente o schema dos models.

É o teste que pega o esquecimento clássico: alguém muda um Column no models.py,
esquece de gerar a migration e só descobre no banco de produção.
"""
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def config_alembic(tmp_path, monkeypatch):
    from alembic.config import Config

    monkeypatch.delenv("DATABASE_URL", raising=False)
    banco = tmp_path / "banco_das_migrations.db"

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{banco.as_posix()}")
    return config


def test_banco_sem_migration_avisa_como_arrumar(tmp_path, monkeypatch):
    """Apontando para um banco vazio, o app avisa em vez de estourar 'no such table'."""
    from sqlalchemy import create_engine

    import main

    vazio = create_engine(f"sqlite:///{(tmp_path / 'vazio.db').as_posix()}")
    monkeypatch.setattr(main, "db", vazio)

    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        main.conferir_banco_migrado()


def test_upgrade_cria_todas_as_tabelas(config_alembic, tmp_path):
    from alembic import command
    from sqlalchemy import create_engine, inspect

    command.upgrade(config_alembic, "head")

    engine = create_engine(config_alembic.get_main_option("sqlalchemy.url"))
    tabelas = set(inspect(engine).get_table_names())
    esperadas = {"users", "companies", "destinations", "platforms", "trips", "status_logs", "app_state"}
    assert esperadas <= tabelas


def test_schema_da_migration_bate_com_os_models(config_alembic):
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    from models import Base

    command.upgrade(config_alembic, "head")

    engine = create_engine(config_alembic.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        diferencas = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert diferencas == [], f"migration fora dos models: {diferencas}"


def test_downgrade_apaga_tudo(config_alembic):
    from alembic import command
    from sqlalchemy import create_engine, inspect

    command.upgrade(config_alembic, "head")
    command.downgrade(config_alembic, "base")

    engine = create_engine(config_alembic.get_main_option("sqlalchemy.url"))
    restantes = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert restantes == set()


def test_head_esta_marcado_apos_upgrade(config_alembic):
    from alembic import command
    from sqlalchemy import create_engine, text

    command.upgrade(config_alembic, "head")

    engine = create_engine(config_alembic.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
