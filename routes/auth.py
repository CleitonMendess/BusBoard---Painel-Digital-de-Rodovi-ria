# auth.py → login e autenticação
from fastapi import APIRouter, Depends, HTTPException
from models import User, db
from dependecies import session_parametr, verificar_token
from main import bcrypt_context, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from schemas import UserSchema, LoginSchema, RoleSchema
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
    return user
#Def para gerar token com jwt
def creat_token(id, duracao_token=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    exp = datetime.now(timezone.utc) + duracao_token
    dic_info = {"sub" : str(id), "exp" : int(exp.timestamp())}
    encode_jwt = jwt.encode(dic_info, SECRET_KEY, ALGORITHM )
    return encode_jwt


#Def para autenticar o user
def autenticar_user(email, password, session):
     user = session.query(User).filter(User.email==email).first()
     if not user:
            return False
     elif not bcrypt_context.verify(password, user.password_hash):
          return False
     return user 


@auth_router.get("/")
async def home():
    """"
Rota padrão de login do sistema
    """
    return{"mensagem" : "Você acessou a rota de login"}

@auth_router.post("/creat_user")
async def creat_user(
    usuario: UserSchema,
    session: Session = Depends(session_parametr),
    current_user: User | None = Depends(verificar_token_opcional), #verificar se existe token ou é none
):

    user = session.query(User).filter(User.email == usuario.email).first()
    if user:
        raise HTTPException(status_code=400, detail="E-mail do usuário já cadastrado")

    # Se pedirem ADM, só deixa continuar quando o usuário logado também for ADM.
    role_solicitado = (usuario.role or "commom").lower()
    if role_solicitado == "adm" and (not current_user or current_user.role != "adm"):
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem criar contas Admin",
        )

    role_final = "adm" if role_solicitado == "adm" else "commom"

    password_crypt = bcrypt_context.hash(usuario.password)
    new_user = User(usuario.name, usuario.email, password_crypt, role_final, usuario.active)
    session.add(new_user)
    session.commit()
    return {"mensagem": f"Usuário cadastrado com sucesso {usuario.email}", "role": role_final}

"""Alterar a role para adm ou commom"""
@auth_router.patch("/users/{user_id}/role")
async def changes_role(role_shema: RoleSchema, user_id: int,
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
    role_normalizada = role_shema.role.lower()
    if role_normalizada not in {"adm", "commom"}:
        raise HTTPException(status_code=400, detail="Role inválida")

    user.role = role_normalizada
    session.commit()
    session.refresh(user)

    return {
        "mensagem": "Role atualizada com sucesso",
        "user_id": user.id,
        "role_atual": user.role,
    }


#login -> email e senha - > token JWT 
@auth_router.post("/login")
async def login (login_schema: LoginSchema, session: Session = Depends(session_parametr)):
    user = autenticar_user(login_schema.email, login_schema.password, session)
    if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado ou credenciais inválidas ")
    else:
         access_token = creat_token(user.id)
         refresh_token = creat_token(user.id, duracao_token=timedelta(days=7))
         return{"access_token": access_token,
                "refresh_token": refresh_token, #dura 7 dias
                "token_type" : "Bearer"}




@auth_router.post("/login-form")
async def login_form (dados_formulario: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(session_parametr)):
    user = autenticar_user(dados_formulario.username, dados_formulario.password, session)
    if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado ou credenciais inválidas ")
    else:
         access_token = creat_token(user.id)
         return{"access_token": access_token,
                "token_type" : "Bearer"}


    

@auth_router.get("/refresh")
async def user_refresh_token(user: User = Depends(verificar_token)):
    access_token = creat_token(user.id)
    return{"access_token": access_token,
            "token_type" : "Bearer"}


