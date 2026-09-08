
'''Função com objetivo de criar uma sessão no BD e dar essa sessão uma resposta como parametro para ser usado no async def '''
from models import db
from sqlalchemy.orm import sessionmaker

def session_parametr():
    try:
        Session = sessionmaker(bind=db)
        session = Session()
        yield session
    finally:
        session.close()
