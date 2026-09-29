"""Cria (ou redefine) a conta de administrador do BusBoard.

Por que existe: a rota POST /auth/creat_user só cria um admin quando já existe
outro admin logado (ver routes/auth.py). Numa instalação nova não há ninguém
logado, então não haveria caminho para o primeiro admin. Este script é esse
caminho — roda fora do servidor, direto no banco.

Uso:
    python criar_admin.py --email admin@busboard.com --nome "Seu Nome"
    python criar_admin.py --email admin@busboard.com --redefinir

A senha é pedida no terminal (não vai para o histórico do shell). Para
automatizar, use --senha, sabendo que ela fica visível no histórico.
"""
import argparse
import getpass
import sys

# Importar main valida o .env e confere se as tabelas existem (Alembic rodou?).
# Se algo estiver errado, o erro sai aqui com a mensagem certa.
import main  # noqa: F401  (o import valida a configuração)
from models import User, db
from senhas import gerar_hash
from sqlalchemy.orm import sessionmaker

TAMANHO_MINIMO_SENHA = 8


def ler_senha(senha: str | None) -> str:
    if senha is not None:
        if len(senha) < TAMANHO_MINIMO_SENHA:
            sys.exit(
                f"A senha precisa ter ao menos {TAMANHO_MINIMO_SENHA} caracteres."
            )
        return senha

    while True:
        senha = getpass.getpass("Senha do admin: ")
        if len(senha) < TAMANHO_MINIMO_SENHA:
            print(f"A senha precisa ter ao menos {TAMANHO_MINIMO_SENHA} caracteres.")
            continue
        if senha == getpass.getpass("Repita a senha: "):
            return senha
        print("As senhas não bateram. Tente de novo.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cria a primeira conta de administrador do BusBoard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--email", required=True, help="E-mail de login do admin")
    parser.add_argument("--nome", default="Administrador", help="Nome exibido no painel")
    parser.add_argument("--senha", help="Senha. Se omitir, o script pergunta no terminal")
    parser.add_argument(
        "--redefinir",
        action="store_true",
        help="Se o e-mail já existir, troca a senha e promove a admin",
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        sys.exit(f"'{args.email}' não parece um e-mail válido.")

    senha = ler_senha(args.senha)
    hash_ = gerar_hash(senha)

    SessionLocal = sessionmaker(bind=db)
    with SessionLocal() as session:
        existente = session.query(User).filter(User.email == email).first()

        if existente and not args.redefinir:
            sys.exit(
                f"Já existe um usuário com o e-mail {email} "
                f"(função: {existente.role}). Use --redefinir para trocar a senha dele."
            )

        if existente:
            existente.name = args.nome
            existente.password_hash = hash_
            existente.role = "adm"
            existente.active = True
            print(f"Senha redefinida e {email} agora é admin.")
        else:
            session.add(User(args.nome, email, hash_, "adm", True))
            print(f"Admin criado: {email}")

        session.commit()

    print("Pronto. Já pode subir o servidor e entrar com esse e-mail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
