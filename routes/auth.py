# auth.py → login e autenticação
from fastapi import APIRouter, Depends, HTTPException
from models import User, db
from sqlalchemy.orm import sessionmaker
from dependecies import session_parametr
from main import bcrypt_context
from schemas import UserSchema
from sqlalchemy.orm import Session

auth_router = APIRouter(prefix="/auth", tags=["auth"])

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


    