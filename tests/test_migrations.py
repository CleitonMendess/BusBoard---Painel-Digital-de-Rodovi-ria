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


# --- trips.trip_direction NOT NULL (7a1c4e8b2f30) ---
#
# O banco real foi criado antes de a coluna existir; a migration inicial marcou
# a revision como aplicada sem reconstruir a tabela, então a coluna ficou
# nullable no banco e NOT NULL no model. Numa base nova o drift não aparece
# (a migration inicial já cria NOT NULL) — os testes de schema acima não
# enxergam isso. Estes testes atacam a migration de correção.

def _coluna(conn, tabela, nome):
    for linha in conn.execute(f"PRAGMA table_info({tabela})"):
        if linha[1] == nome:
            return linha
    return None


def _caminho_do_banco(config_alembic):
    """O caminho do arquivo SQLite que o Alembic vai usar.

    Não montar o caminho à mão com replace: o CI roda em Linux e o caminho
    seria diferente do que os testes abrem (o teste passava escrevendo num
    arquivo e lendo outro). O SQLAlchemy já sabe converter a URL.
    """
    from sqlalchemy.engine import make_url

    caminho = make_url(config_alembic.get_main_option("sqlalchemy.url")).database
    return pathlib.Path(caminho)


def _criar_trips_nullable(banco):
    """Uma tabela trips no estado antigo: mesma estrutura, coluna nullable."""
    import sqlite3

    conn = sqlite3.connect(banco)
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name VARCHAR, active BOOLEAN);
        CREATE TABLE destinations (id INTEGER PRIMARY KEY, city VARCHAR, state VARCHAR, active BOOLEAN);
        CREATE TABLE platforms (id INTEGER PRIMARY KEY, number INTEGER, active BOOLEAN);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, email VARCHAR,
                            password_hash VARCHAR, role VARCHAR, active BOOLEAN,
                            created_at DATETIME NOT NULL);
        CREATE TABLE trips (
            id INTEGER PRIMARY KEY,
            type VARCHAR NOT NULL,
            scheduled_time VARCHAR NOT NULL,
            estimated_time VARCHAR,
            status VARCHAR(255),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            company_id INTEGER REFERENCES companies(id),
            destination_id INTEGER REFERENCES destinations(id),
            platform_id INTEGER REFERENCES platforms(id),
            trip_direction VARCHAR
        );
        INSERT INTO companies (id, name) VALUES (1, 'Rodoviaria X');
        INSERT INTO trips (type, trip_direction, scheduled_time, created_at, updated_at, company_id)
        VALUES ('INTERESTADUAL', 'SAIDA', '08:00', '2026-01-01 08:00:00', '2026-01-01 08:00:00', 1),
               ('LOCAL', 'CHEGADA', '10:00', '2026-01-01 08:00:00', '2026-01-01 08:00:00', 1);
        """
    )
    conn.commit()
    conn.close()


def _marcar_ate_a_migration_anterior(banco):
    """Deixa o banco no ponto anterior à migration de correção."""
    import sqlite3

    conn = sqlite3.connect(banco)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version VALUES ('c652b4563588')")
    conn.commit()
    conn.close()


def test_migration_torna_trip_direction_not_null(config_alembic):
    from alembic import command
    from sqlalchemy import create_engine

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    command.upgrade(config_alembic, "7a1c4e8b2f30")

    import sqlite3

    conn = sqlite3.connect(banco)
    try:
        coluna = _coluna(conn, "trips", "trip_direction")
        assert coluna is not None
        assert coluna[3] == 1, "trip_direction continua aceitando NULL"
    finally:
        conn.close()


def test_migration_preserva_as_viagens(config_alembic):
    """A migration recria a tabela no SQLite; os dados têm que sobreviver."""
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    import sqlite3

    antes = sqlite3.connect(banco)
    try:
        viagens = antes.execute(
            "SELECT id, type, trip_direction, scheduled_time FROM trips ORDER BY id"
        ).fetchall()
    finally:
        antes.close()
    assert len(viagens) == 2

    command.upgrade(config_alembic, "7a1c4e8b2f30")

    depois = sqlite3.connect(banco)
    try:
        assert depois.execute(
            "SELECT id, type, trip_direction, scheduled_time FROM trips ORDER BY id"
        ).fetchall() == viagens
    finally:
        depois.close()


def test_migration_mantem_as_chaves_estrangeiras(config_alembic):
    """batch_alter_table reconstrói a tabela: as FKs podem se perder no meio."""
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    def chaves_estrangeiras():
        import sqlite3

        conn = sqlite3.connect(banco)
        try:
            return sorted(
                (linha[2], linha[3], linha[4])
                for linha in conn.execute("PRAGMA foreign_key_list(trips)")
            )
        finally:
            conn.close()

    antes = chaves_estrangeiras()
    assert antes, "o banco de teste deveria ter FKs para comparar"

    command.upgrade(config_alembic, "7a1c4e8b2f30")

    assert chaves_estrangeiras() == antes, "a reconstrução da tabela perdeu FK"


def test_banco_recusa_viagem_sem_direcao_apos_a_migration(config_alembic):
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    command.upgrade(config_alembic, "7a1c4e8b2f30")

    import sqlite3

    conn = sqlite3.connect(banco)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO trips (type, trip_direction, scheduled_time, created_at, updated_at) "
                "VALUES ('LOCAL', NULL, '12:00', '2026-01-01', '2026-01-01')"
            )
        # e uma viagem com direção continua entrando
        conn.execute(
            "INSERT INTO trips (type, trip_direction, scheduled_time, created_at, updated_at) "
            "VALUES ('LOCAL', 'CHEGADA', '12:00', '2026-01-01', '2026-01-01')"
        )
        conn.commit()
    finally:
        conn.close()


def test_migration_recusa_dado_invalido_em_vez_de_apagar(config_alembic):
    """Se aparecer viagem sem direção, a migration para e avisa.

    O caminho automático seria preencher com algo inventado. Perder dado
    silencioso é pior do que exigir uma decisão.
    """
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    import sqlite3

    conn = sqlite3.connect(banco)
    conn.execute("UPDATE trips SET trip_direction = NULL WHERE id = 1")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="trip_direction"):
        command.upgrade(config_alembic, "7a1c4e8b2f30")

    conn = sqlite3.connect(banco)
    try:
        assert conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 2, "a migration apagou viagem"
    finally:
        conn.close()


def test_downgrade_da_migration_devolve_nullable(config_alembic):
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    import sqlite3

    def not_null():
        conn = sqlite3.connect(banco)
        try:
            return _coluna(conn, "trips", "trip_direction")[3]
        finally:
            conn.close()

    command.upgrade(config_alembic, "7a1c4e8b2f30")
    assert not_null() == 1

    command.downgrade(config_alembic, "c652b4563588")
    assert not_null() == 0, "o downgrade não devolveu a coluna para nullable"


def test_ciclo_upgrade_downgrade_upgrade(config_alembic):
    """Dá para reverter e reaplicar, que é o que acontece em deploy de volta."""
    from alembic import command

    banco = _caminho_do_banco(config_alembic)
    _criar_trips_nullable(banco)
    _marcar_ate_a_migration_anterior(banco)

    command.upgrade(config_alembic, "7a1c4e8b2f30")
    command.downgrade(config_alembic, "c652b4563588")
    command.upgrade(config_alembic, "7a1c4e8b2f30")

    import sqlite3

    conn = sqlite3.connect(banco)
    try:
        assert _coluna(conn, "trips", "trip_direction")[3] == 1
        assert conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 2
    finally:
        conn.close()
