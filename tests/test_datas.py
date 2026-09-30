"""O "agora" do sistema, e a regra de fuso que vem com ele.

Python 3.12 depreciou datetime.utcnow(). A troca óbvia seria
datetime.now(timezone.utc), mas aqui isso quebrava: o SQLite não guarda fuso
horário — nem com DateTime(timezone=True) — então a data voltaria do banco
sem tzinfo e a comparação com expires_at estouraria
"can't compare offset-naive and offset-aware datetimes".

A regra do projeto: toda data gravada é UTC sem fuso, e agora_utc() é a
única forma de obter "agora". Estes testes existem para a regra não ser
quebrada por alguém que ache a_DATA strftime_ mais simples.
"""
import datetime
import pathlib

import pytest

from datas import agora_utc

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def test_agora_utc_nao_tem_fuso():
    """O que o SQLite consegue devolver de volta é data sem fuso."""
    assert agora_utc().tzinfo is None


def test_agora_utc_e_utc_de_verdade():
    """Não pode ser hora local: Brasília é 3 horas atrás do UTC, e o banco
    inteiro é lido como UTC."""
    agora = agora_utc()
    utc_real = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    assert abs((utc_real - agora).total_seconds()) < 5


def test_formato_gravado_continua_o_mesmo():
    """O formato não muda, e é por isso que não precisa de migration:
    o utcnow() gravava 2026-09-30 04:11:07.916043 e agora_utc() grava
    exatamente isso."""
    gravado = agora_utc().strftime("%Y-%m-%d %H:%M:%S.%f")
    assert len(gravado) == len("2026-09-30 04:11:07.916043")
    # e o que o SQLAlchemy lê de volta é uma datetime sem fuso
    from sqlalchemy import Column, DateTime, Integer, create_engine
    from sqlalchemy.orm import Session, declarative_base

    base = declarative_base()

    class Convite(base):
        __tablename__ = "convite_fuso_teste"
        id = Column(Integer, primary_key=True)
        expires_at = Column(DateTime)

    engine = create_engine("sqlite:///:memory:")
    base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Convite(id=1, expires_at=agora_utc()))
        s.commit()
    with Session(engine) as s:
        relido = s.query(Convite).first().expires_at

    assert isinstance(relido, datetime.datetime)
    assert relido.tzinfo is None


def test_comparar_data_do_banco_com_agora_utc_funciona():
    """O caminho que quebraria com now(UTC): dado do banco comparado com "agora".

    Se alguém trocar agora_utc() por datetime.now(timezone.utc), este teste
    estoura TypeError em vez de o convite quebrar em produção.
    """
    from sqlalchemy import Column, DateTime, Integer, create_engine
    from sqlalchemy.orm import Session, declarative_base

    base = declarative_base()

    class Convite(base):
        __tablename__ = "convite_comparacao_teste"
        id = Column(Integer, primary_key=True)
        expires_at = Column(DateTime)

    engine = create_engine("sqlite:///:memory:")
    base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Convite(id=1, expires_at=agora_utc()))
        s.commit()
    with Session(engine) as s:
        relido = s.query(Convite).first().expires_at

    # a comparação que _situacao() faz: expirado quando expires_at <= agora
    assert (relido <= agora_utc() - datetime.timedelta(minutes=1)) is False
    assert (relido <= agora_utc() + datetime.timedelta(hours=1)) is True


def test_now_com_fuso_quebraria_contra_dado_do_banco():
    """Documenta o motivo da regra: é este TypeError que a troca ingênua
    provocaria. Se um dia o banco passar a guardar fuso de verdade, é aqui
    que se percebe."""
    do_banco = agora_utc()  # o que o SQLite devolve
    with pytest.raises(TypeError):
        do_banco <= datetime.datetime.now(datetime.UTC)


def test_nenhum_utcnow_sobrou_no_projeto():
    """Nenhuma chamada nova ao utcnow(): ele some em breve no Python, e quem
    chamar de novo reintroduz o aviso."""
    achados = []
    for caminho in RAIZ.rglob("*.py"):
        if any(parte.startswith(".venv") or parte == "node_modules" for parte in caminho.parts):
            continue
        # datas.py e este arquivo mencionam utcnow() de propósito (o docstring
        # e o nome do teste); o que vale e nenhuma CHAMADA nova
        if caminho.name in ("datas.py", "test_datas.py"):
            continue
        if "utcnow" in caminho.read_text(encoding="utf-8", errors="replace"):
            achados.append(str(caminho.relative_to(RAIZ)))
    assert not achados, f"utcnow() de volta em: {achados}"


def test_daily_reset_usa_fuso_local_nao_utc():
    """O reinício diário é a exceção: ele pergunta "que dia é agora, na
    rodoviária?", e a resposta depende do fuso local, não do UTC."""
    import daily_reset

    assert daily_reset.LOCAL_TZ is not None
    hoje = daily_reset.dia_operacional()
    assert len(hoje) == 10 and hoje[4] == "-"


def test_backup_usa_hora_local_para_nomear_arquivo():
    """O nome do arquivo de backup é ordenado por data, então tem que ser
    hora local — em UTC, o arquivo da madrugada sairia com o dia anterior."""
    import backup
    import inspect

    fonte = inspect.getsource(backup)
    assert "utcnow" not in fonte
    assert "datetime.now()" in fonte
