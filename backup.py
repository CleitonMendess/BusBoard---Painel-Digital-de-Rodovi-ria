"""Backup do banco de dados.

O SQLite é um arquivo só, e a rodoviária perde o dia se ele sumir. Este módulo
tira uma cópia consistente usando o `backup()` do próprio SQLite: diferente de
copiar o arquivo com shutil, ele funciona mesmo com o servidor escrevendo ao
mesmo tempo (não pega o banco no meio de uma transação).

Dois jeitos de usar:

1. Automático, junto com o reinício diário (ver daily_reset.py): uma cópia por
   dia, logo depois de virar o dia — é o retrato do dia anterior fechando.
2. Na mão, para um agendamento do sistema:

       python backup.py                  # um backup agora
       python backup.py --manter 30      # e guarda os últimos 30

   No Windows, use o Agendador de Tarefas; no Linux, o cron:

       0 */2 * * *  cd /caminho/busboard && .venv/bin/python backup.py

Configuração opcional no .env:
   BACKUP_PASTA=backups   onde guardar. Padrão: ./backups
   BACKUP_MANTER=14       quantos backups antigos preservar. Padrão: 14
"""
import argparse
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from models import db

PASTA_PADRAO = os.getenv("BACKUP_PASTA", "backups").strip() or "backups"
MANTER_PADRAO = 14
PREFIXO = "banco-"
SUFIXO = ".db"

log = logging.getLogger("busboard.backup")


def caminho_do_banco() -> str:
    """Caminho do arquivo SQLite que o app está usando."""
    url = make_url(db.url)
    if url.get_backend_name() != "sqlite":
        raise RuntimeError(
            f"Backup só funciona com SQLite; o app está em {url.get_backend_name()}. "
            "Use o backup nativo do banco (pg_dump, mysqldump, ...)."
        )
    if not url.database or url.database == ":memory:":
        raise RuntimeError("O banco está em memória: não há arquivo para copiar.")
    return str(Path(url.database).resolve())


def criar_backup(
    pasta: str | Path | None = None,
    manter: int | None = None,
    caminho: str | Path | None = None,
) -> Path:
    """Cria uma cópia consistente do banco e limpa as antigas.

    Devolve o caminho do arquivo criado.
    """
    destino_pasta = Path(pasta) if pasta is not None else Path(PASTA_PADRAO)
    destino_pasta.mkdir(parents=True, exist_ok=True)

    origem_caminho = str(caminho) if caminho is not None else caminho_do_banco()
    origem = Path(origem_caminho)
    if not origem.exists():
        raise FileNotFoundError(f"Banco não encontrado: {origem}")

    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = destino_pasta / f"{PREFIXO}{carimbo}{SUFIXO}"
    if destino.exists():  # dois backups no mesmo segundo
        destino = destino_pasta / f"{PREFIXO}{carimbo}-{os.getpid()}{SUFIXO}"

    with closing(sqlite3.connect(origem)) as origem_db:
        with closing(sqlite3.connect(destino)) as destino_db:
            origem_db.backup(destino_db)
            destino_db.commit()

    log.info(f"Backup criado: {destino}")
    apagar_antigos(destino_pasta, manter)
    return destino


def apagar_antigos(pasta: str | Path | None = None, manter: int | None = None) -> list[Path]:
    """Mantém os `manter` backups mais novos (contando o que acabou de ser criado)
    e apaga o resto. `manter=0` não joga fora a cópia nova: no mínimo fica uma."""
    if manter is None:
        manter = int(os.getenv("BACKUP_MANTER", str(MANTER_PADRAO)))
    limite = max(1, manter)
    destino_pasta = Path(pasta) if pasta is not None else Path(PASTA_PADRAO)

    # o nome tem data/hora no formato, então ordenar pelo nome é ordenar por data
    backups = sorted(destino_pasta.glob(f"{PREFIXO}*{SUFIXO}"))
    apagados = []
    for velho in backups[: max(0, len(backups) - limite)]:
        velho.unlink()
        apagados.append(velho)
    for velho in apagados:
        log.info("Backup antigo removido: %s", velho)
    return apagados



def main() -> int:
    parser = argparse.ArgumentParser(description="Faz um backup do banco do BusBoard.")
    parser.add_argument("--pasta", help=f"Onde guardar. Padrão: {PASTA_PADRAO}")
    parser.add_argument(
        "--manter",
        type=int,
        help=f"Quantos backups preservar. Padrão: {MANTER_PADRAO} (ou BACKUP_MANTER)",
    )
    args = parser.parse_args()

    # este script roda sozinho, sem o main: configura o log na mão para o
    # progresso aparecer e para o log.info não ser descartado
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        force=True,
    )

    arquivo = criar_backup(pasta=args.pasta, manter=args.manter)
    tamanho_kb = arquivo.stat().st_size / 1024
    print(f"Backup criado: {arquivo} ({tamanho_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
