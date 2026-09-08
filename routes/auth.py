# auth.py → login e autenticação
from fastapi import APIRouter, Depends
from models import User, db
from sqlalchemy.orm import sessionmaker
from dependecies import session_parametr
from main import bcrypt_context

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.get("/")
async def home():
    """"
Rota padrão de loguin do sistema
    """
    return{"mensagem" : "Você acessou a rota de login"}

@auth_router.post("/creat_user")
async def creat_user(name: str, email: str, username: str, password_hash: str, session = Depends(session_parametr),):

    user =  session.query(User).filter(User.username==username).first()
    if user:
        return {"mensagem": "Usuário já existe com esse username"}
    else:
        password_crypt = bcrypt_context.hash(password_hash)
        new_user = User(email, name, username, password_crypt)
        session.add(new_user)
        session.commit()
        return {"mensagem": "Usuário cadastrado com sucesso"}


    