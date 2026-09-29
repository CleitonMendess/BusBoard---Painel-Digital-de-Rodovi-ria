# invites.py → cadastro por convite
#
# A tela de login é só para entrar. Criar conta não é aberto: quem cria é o
# administrador, que gera um convite com validade. Assim, saber o endereço do
# painel não basta para virar usuário — precisa do código, que o admin manda
# para quem ele quer na equipe.
#
# O código vai uma vez só na resposta (é o mesmo esquema do link de redefinição
# de senha). No banco fica só o hash: se o banco vazar, os convites pendentes
# não viram conta pronta para ninguém.
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from dependecies import session_parametr, verificar_admin
from main import bcrypt_context
from models import Invite, User
from rate_limit import chave_login, registrar_falha, registrar_sucesso, tentar_login
from routes.auth import create_token
from schemas import InviteCheckSchema, InviteCreateSchema, InviteSchema, RegisterSchema

log = logging.getLogger("busboard.convites")

invites_router = APIRouter(prefix="/auth", tags=["convites"])

# Validade padrão, em horas. O .env pode mudar (INVITE_VALIDADE_HORAS).
VALIDADE_PADRAO_HORAS = int(os.getenv("INVITE_VALIDADE_HORAS", "72"))
SENHA_MINIMA = 8
EMAILS = {"adm", "operador"}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _situacao(convite: Invite, agora: datetime | None = None) -> str:
    momento = agora or datetime.utcnow()
    if convite.used_at is not None:
        return "usado"
    if convite.expires_at <= momento:
        return "expirado"
    return "pendente"


def _convite_de(token: str, session: Session) -> Invite:
    """Acha o convite pelo código. Erro genérico de propósito: um código
    inexistente, usado ou vencido leva à mesma resposta, para não dar para
    testar código por tentativa e erro."""
    convite = session.query(Invite).filter(Invite.token_hash == _hash(token)).first()
    if convite is None:
        raise HTTPException(status_code=404, detail="Convite inválido, usado ou expirado.")
    return convite


def _serializar(convite: Invite, session: Session) -> dict:
    usado_por = None
    if convite.used_by:
        usuario = session.get(User, convite.used_by)
        usado_por = usuario.email if usuario else None
    return {
        "id": convite.id,
        "role": convite.role,
        "created_at": convite.created_at,
        "expires_at": convite.expires_at,
        "used_at": convite.used_at,
        "usado_por": usado_por,
        "situacao": _situacao(convite),
    }


# ---------- administração dos convites ----------

@invites_router.post("/invites", status_code=201)
def criar_convite(
    dados: InviteCreateSchema,
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    """Gera um convite. O código aparece aqui e não tem como ver de novo."""
    role = (dados.role or "operador").lower()
    if role not in EMAILS:
        raise HTTPException(status_code=400, detail="Função inválida: use adm ou operador")

    validade = VALIDADE_PADRAO_HORAS if dados.validade_horas is None else dados.validade_horas
    if validade <= 0 or validade > 24 * 90:
        raise HTTPException(
            status_code=400,
            detail="A validade precisa ser entre 1 e 2160 horas (90 dias)",
        )

    token = secrets.token_urlsafe(24)
    agora = datetime.utcnow()
    convite = Invite(
        token_hash=_hash(token),
        role=role,
        created_by=current_user.id,
        expires_at=agora + timedelta(hours=validade),
    )
    session.add(convite)
    session.commit()
    session.refresh(convite)
    log.info(
        "Convite %s criado por %s (válido até %s)",
        convite.id,
        current_user.email,
        convite.expires_at,
    )

    return {
        "id": convite.id,
        "token": token,
        "role": role,
        "expires_at": convite.expires_at,
        "link": f"/cadastro/{token}",
        "aviso": "O código aparece só agora. Copie e envie para a pessoa.",
    }


@invites_router.get("/invites")
def listar_convites(
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    """Convites mais novos primeiro, para o admin ver o que ainda vale."""
    agora = datetime.utcnow()
    convites = (
        session.query(Invite)
        .order_by(Invite.created_at.desc(), Invite.id.desc())
        .all()
    )
    return {"Convites": [_serializar(c, session) for c in convites], "agora": agora}


@invites_router.delete("/invites/{convite_id}")
def cancelar_convite(
    convite_id: int,
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    """Cancela um convite pendente. Usado não sai: o registro fica como histórico."""
    convite = session.get(Invite, convite_id)
    if convite is None:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if convite.used_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Esse convite já foi usado, então não há o que cancelar",
        )

    session.delete(convite)
    session.commit()
    log.info("Convite %s cancelado por %s", convite_id, current_user.email)
    return {"mensagem": "Convite cancelado", "id": convite_id}


# ---------- uso do convite (sem login) ----------

@invites_router.get("/invites/{token}", response_model=InviteCheckSchema)
def checar_convite(token: str, session: Session = Depends(session_parametr)):
    """O front chama isto antes de mostrar o formulário de cadastro."""
    convite = session.query(Invite).filter(Invite.token_hash == _hash(token)).first()
    if convite is None:
        return {"valido": False, "motivo": "Convite inválido, usado ou expirado."}

    situacao = _situacao(convite)
    if situacao == "usado":
        return {"valido": False, "motivo": "Este convite já foi usado."}
    if situacao == "expirado":
        return {"valido": False, "motivo": "Este convite expirou. Peça um novo ao administrador."}

    return {"valido": True, "role": convite.role}


@invites_router.post("/registrar")
def registrar(dados: RegisterSchema, request: Request, session: Session = Depends(session_parametr)):
    """Cria a conta a partir do convite e já deixa a pessoa logada."""
    email = (dados.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido")
    if len(dados.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Escreva seu nome")
    if len(dados.password) < SENHA_MINIMA:
        raise HTTPException(
            status_code=400,
            detail=f"A senha precisa de pelo menos {SENHA_MINIMA} caracteres",
        )

    # mesma trava do login: Registration público também não pode ficar em loop
    chave = chave_login(f"cadastro:{email}", request.client.host)
    espera = tentar_login(chave)
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Tente de novo em {espera} segundo(s).",
            headers={"Retry-After": str(espera)},
        )

    convite = _convite_de(dados.token, session)
    situacao = _situacao(convite)
    if situacao != "pendente":
        registrar_falha(chave)
        raise HTTPException(status_code=400, detail="Este convite já foi usado ou expirou.")

    if session.query(User).filter(User.email == email).first():
        registrar_falha(chave)
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    novo = User(
        dados.name.strip(),
        email,
        bcrypt_context.hash(dados.password),
        convite.role,
        True,
    )
    session.add(novo)
    session.commit()
    session.refresh(novo)

    agora = datetime.utcnow()
    convite.used_at = agora
    convite.used_by = novo.id
    session.commit()
    registrar_sucesso(chave)
    log.info("Cadastro pelo convite %s: %s (%s)", convite.id, novo.email, novo.role)

    return {
        "mensagem": "Conta criada. Bom trabalho!",
        "access_token": create_token(novo.id),
        "refresh_token": create_token(novo.id, duracao_token=timedelta(days=7)),
        "token_type": "Bearer",
        "role": novo.role,
    }
