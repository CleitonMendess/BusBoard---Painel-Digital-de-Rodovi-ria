# auth.py → login e autenticação
from fastapi import APIRouter

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.get("/")
async def autenticar():
    """"
Rota padrão de loguin do sistema
    """
    return{"mensagem" : "Você acessou a rota de login"}