
'''Função com objetivo de criar uma sessão no BD e dar essa sessão uma resposta como parametro para ser usado no async def '''
from fastapi import Depends, HTTPException
from main import SECRET_KEY, ALGORITHM, oauth2_schema
from models import db, User
from sqlalchemy.orm import sessionmaker, Session
from jose import jwt, JWTError


def session_parametr():
    try:
        Session = sessionmaker(bind=db)
        session = Session()
        yield session
    finally:
        session.close()


def verificar_token(token: str = Depends(oauth2_schema), session: Session = Depends(session_parametr)):
    try:
        dic_info = jwt.decode(token, SECRET_KEY, ALGORITHM)
        user_id = int(dic_info.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Acesso Negado, verifique a validade do token")
    # Verificar se o token é valido
    # Extrair o ID do usuário do token
    user = session.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Acesso Inválido")
    return user

def verificar_admin(user: User = Depends(verificar_token)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Acesso negado: requer permissão de administrador")
    return user