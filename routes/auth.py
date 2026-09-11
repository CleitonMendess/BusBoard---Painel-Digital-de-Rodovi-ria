# auth.py → login e autenticação
from fastapi import APIRouter, Depends, HTTPException
from models import User, db
from sqlalchemy.orm import sessionmaker
from dependecies import session_parametr
from main import bcrypt_context
from schemas import UserSchema, LoginSchema
from sqlalchemy.orm import Session

auth_router = APIRouter(prefix="/auth", tags=["auth"])

def creat_token(id):
    token = f"YjtZy9bMZq3I2Lkv4LfUKjbkh{id}Af47vzUh9KFW5Aq6HDYtELfcbGhMK8EQaAmcX4y"
    return token

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
Rota padrão de loguin do sistema
    """
    return{"mensagem" : "Você acessou a rota de login"}

@auth_router.post("/creat_user")
async def creat_user(usuario: UserSchema, session: Session = Depends(session_parametr)):

    user = session.query(User).filter(User.email == usuario.email).first()
    if user:
        raise HTTPException(status_code=400, detail="E-mail do usuário já cadastrado")

    else:
        password_crypt = bcrypt_context.hash(usuario.password)
        new_user = User(usuario.name, usuario.email, password_crypt, usuario.role or "commom", usuario.active)
        session.add(new_user)
        session.commit()
        return {"mensagem": f"Usuário cadastrado com sucesso {usuario.email}"}

#login -> email e senha - > token JWT 
@auth_router.post("/login")
async def login (login_schema: LoginSchema, session: Session = Depends(session_parametr)):
    user = autenticar_user(login_schema.email, login_schema.password, session)
    if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado ou credenciais inválidas ")
    else:
         access_token = creat_token(user.id)
         return{"access_token": access_token,
                "token_type" : "Bearer"}
