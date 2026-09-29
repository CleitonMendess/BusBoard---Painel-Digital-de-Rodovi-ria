# auth.py → login e autenticação
from fastapi import APIRouter, Depends, HTTPException, Request
from models import User, StatusLog, db
from dependecies import session_parametr, verificar_token, verificar_admin
from main import ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from rate_limit import chave_login, registrar_falha, registrar_sucesso, tentar_login
from schemas import UserSchema, LoginSchema, RoleSchema, ActiveSchema, RefreshSchema
from senhas import gerar_hash, verificar_senha
from sqlalchemy.orm import Session, sessionmaker
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer



auth_router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_schema_optional = OAuth2PasswordBearer(tokenUrl="auth/login-form", auto_error=False)


# Tenta identificar o usuário logado, mas não obriga autenticação.
def verificar_token_opcional(token: str | None = Depends(oauth2_schema_optional), session: Session = Depends(session_parametr)):
    if not token:
        return None

    try:
        dic_info = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(dic_info.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None

    user = session.query(User).filter(User.id == user_id).first()
    if user and user.active is False:
        return None
    return user
#Def para gerar token com jwt
def create_token(id, duracao_token=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    exp = datetime.now(timezone.utc) + duracao_token
    dic_info = {"sub" : str(id), "exp" : int(exp.timestamp())}
    encode_jwt = jwt.encode(dic_info, SECRET_KEY, ALGORITHM )
    return encode_jwt


#Def para autenticar o user
def autenticar_user(email, password, session):
     user = session.query(User).filter(User.email==email).first()
     if not user:
            return False
     elif not verificar_senha(password, user.password_hash):
          return False
     if user.active is False:
          raise HTTPException(status_code=403, detail="Usuário inativo. Fale com o administrador.")
     return user 


@auth_router.get("/")
def home():
    """"
Rota padrão de login do sistema
    """
    return{"mensagem" : "Você acessou a rota de login"}

@auth_router.post("/creat_user")
def create_user(
    usuario: UserSchema,
    session: Session = Depends(session_parametr),
    current_user: User | None = Depends(verificar_token_opcional), #verificar se existe token ou é none
):

    user = session.query(User).filter(User.email == usuario.email).first()
    if user:
        raise HTTPException(status_code=400, detail="E-mail do usuário já cadastrado")

    # Se pedirem ADM, só deixa continuar quando o usuário logado também for ADM.
    role_solicitado = (usuario.role or "operador").lower()
    if role_solicitado == "adm" and (not current_user or current_user.role != "adm"):
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem criar contas Admin",
        )

    role_final = "adm" if role_solicitado == "adm" else "operador"

    password_crypt = gerar_hash(usuario.password)
    new_user = User(usuario.name, usuario.email, password_crypt, role_final, usuario.active)
    session.add(new_user)
    session.commit()
    return {"mensagem": f"Usuário cadastrado com sucesso {usuario.email}", "role": role_final}

"""Alterar a role para adm ou operador"""
@auth_router.patch("/users/{user_id}/role")
def changes_role(role_shema: RoleSchema, user_id: int,
session: Session = Depends(session_parametr),
current_user: User | None = Depends(verificar_token_opcional)):

    if not current_user or current_user.role != "adm":
        raise HTTPException(
            status_code=403,
            detail="Apenas usuarios administradores podem mudar a função"
        )

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=" O usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode mudar a sua própria função")
    role_normalizada = role_shema.role.lower()
    if role_normalizada not in {"adm", "operador"}:
        raise HTTPException(status_code=400, detail="Role inválida")

    user.role = role_normalizada
    session.commit()
    session.refresh(user)

    return {
        "mensagem": "Role atualizada com sucesso",
        "user_id": user.id,
        "role_atual": user.role,
    }


@auth_router.patch("/users/{user_id}/active")
def change_user_active(
    user_id: int,
    active_schema: ActiveSchema,
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    """Ativa ou desativa um usuário (desativado não consegue mais entrar)."""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id and not active_schema.active:
        raise HTTPException(status_code=400, detail="Você não pode desativar o seu próprio usuário")

    user.active = active_schema.active
    session.commit()
    situacao = "ativado" if user.active else "desativado"
    return {"mensagem": f"Usuário {user.name} {situacao} com sucesso", "user_id": user.id, "active": user.active}


@auth_router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    """Exclui um usuário. O histórico de status é mantido, só perde o nome de quem mudou."""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir o seu próprio usuário")

    nome = user.name
    session.query(StatusLog).filter(StatusLog.changed_by == user.id).update({StatusLog.changed_by: None})
    session.delete(user)
    session.commit()
    return {"mensagem": f"Usuário {nome} excluído com sucesso"}


#login -> email e senha - > token JWT 
@auth_router.post("/login")
def login (login_schema: LoginSchema, request: Request, session: Session = Depends(session_parametr)):
    chave = chave_login(login_schema.email, request.client.host)
    espera = tentar_login(chave)
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente de novo em {espera} segundo(s).",
            headers={"Retry-After": str(espera)},
        )

    user = autenticar_user(login_schema.email, login_schema.password, session)
    if not user:
        registrar_falha(chave)
        raise HTTPException(status_code=400, detail="Usuário não encontrado ou credenciais inválidas ")

    registrar_sucesso(chave)
    access_token = create_token(user.id)
    refresh_token = create_token(user.id, duracao_token=timedelta(days=7))
    return{"access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "role": user.role}




@auth_router.post("/login-form")
def login_form (request: Request, dados_formulario: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(session_parametr)):
    chave = chave_login(dados_formulario.username, request.client.host)
    espera = tentar_login(chave)
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente de novo em {espera} segundo(s).",
            headers={"Retry-After": str(espera)},
        )

    user = autenticar_user(dados_formulario.username, dados_formulario.password, session)
    if not user:
        registrar_falha(chave)
        raise HTTPException(status_code=400, detail="Usuário não encontrado ou credenciais inválidas ")

    registrar_sucesso(chave)
    return{"access_token": create_token(user.id),
            "token_type" : "Bearer"}


    

@auth_router.post("/refresh")
def user_refresh_token(
    dados: RefreshSchema,
    session: Session = Depends(session_parametr),
):
    """Troca o refresh_token (de 7 dias) por um access_token novo.

    Não usa o access_token de propósito: é justamente quando ele já expirou
    que o front precisa renovar a sessão.
    """
    try:
        dic_info = jwt.decode(dados.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(dic_info.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Acesso Inválido")
    if user.active is False:
        raise HTTPException(status_code=401, detail="Usuário inativo")

    return{"access_token": create_token(user.id),
            "token_type" : "Bearer"}

@auth_router.get("/users")
def list_users(
    session: Session = Depends(session_parametr),
    current_user: User = Depends(verificar_admin),
):
    users = session.query(User).all()
    return {"Usuarios": [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "active": u.active}
        for u in users
    ]}