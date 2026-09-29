"""Backup do banco: a cópia tem que ser fiel e os antigos têm que sumir."""
import sqlite3

import pytest

import backup


@pytest.fixture
def banco_com_dados(tmp_path):
    """Um SQLite de verdade, com tabela e linhas, para copiar."""
    caminho = tmp_path / "origem.db"
    with sqlite3.connect(caminho) as conn:
        conn.execute("CREATE TABLE viagem (id INTEGER PRIMARY KEY, destino TEXT)")
        conn.executemany(
            "INSERT INTO viagem (destino) VALUES (?)",
            [("Guarulhos",), ("Campinas",)],
        )
        conn.commit()
    return caminho


def contar(arquivo, tabela="viagem"):
    with sqlite3.connect(arquivo) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_backup_copia_os_dados(banco_com_dados, tmp_path):
    destino = backup.criar_backup(pasta=tmp_path / "backups", caminho=banco_com_dados)

    assert destino.exists()
    assert contar(destino) == contar(banco_com_dados) == 2


def test_backup_e_um_arquivo_valido(banco_com_dados, tmp_path):
    destino = backup.criar_backup(pasta=tmp_path / "backups", caminho=banco_com_dados)

    with sqlite3.connect(destino) as conn:
        destinos = [linha[0] for linha in conn.execute("SELECT destino FROM viagem")]

    assert destinos == ["Guarulhos", "Campinas"]


def test_backup_nao_apaga_o_banco_original(banco_com_dados, tmp_path):
    backup.criar_backup(pasta=tmp_path / "backups", caminho=banco_com_dados)

    assert banco_com_dados.exists()
    assert contar(banco_com_dados) == 2


def test_backup_preserva_so_os_mais_novos(banco_com_dados, tmp_path):
    pasta = tmp_path / "backups"
    pasta.mkdir()
    # nomes antigos com o mesmo formato: o mais recente é o do meio do nome
    for dia in ("20260101-030000", "20260102-030000", "20260103-030000", "20260104-030000"):
        (pasta / f"banco-{dia}.db").write_bytes(b"velho")

    backup.criar_backup(pasta=pasta, manter=2, caminho=banco_com_dados)

    restantes = sorted(p.name for p in pasta.glob("banco-*.db"))
    # manter=2 conta o backup novo: fica ele e o mais recente dos antigos
    assert len(restantes) == 2
    assert "banco-20260104-030000.db" in restantes
    for dia in ("20260101-030000", "20260102-030000", "20260103-030000"):
        assert not (pasta / f"banco-{dia}.db").exists()


def test_manter_zero_ainda_preserva_o_backup_novo(banco_com_dados, tmp_path):
    pasta = tmp_path / "backups"
    pasta.mkdir()
    (pasta / "banco-20260101-030000.db").write_bytes(b"velho")

    destino = backup.criar_backup(pasta=pasta, manter=0, caminho=banco_com_dados)

    # manter=0 quer dizer "não guarde nenhum antigo", não "jogue fora a cópia de agora"
    assert [p.name for p in pasta.glob("banco-*.db")] == [destino.name]
    assert contar(destino) == 2


def test_banco_inexistente_falha_claro(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup.criar_backup(pasta=tmp_path / "backups", caminho=tmp_path / "nao_existe.db")


def test_banco_em_memoria_avisa_que_nao_da_para_copiar(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "db", _engine_em_memoria())

    with pytest.raises(RuntimeError, match="memória"):
        backup.criar_backup(pasta=tmp_path / "backups")


def _engine_em_memoria():
    from sqlalchemy import create_engine

    return create_engine("sqlite://")
