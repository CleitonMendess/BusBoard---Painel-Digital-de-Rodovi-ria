# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter

trips_router = APIRouter(prefix="/trips", tags=["trips"])

""""
Apenas listar pode ser acessado por um usuario que não é ADM
    """
@trips_router.get("/")
async def viagens():
    return {"mensagen" : "Você está acessando a pagina de viagens"}

@trips_router.get("/listar")
async def listar():
    return {"mensagen" : "Def para listar as viagens"}

@trips_router.get("/criar")
async def criar():
    return {"mensagen" : "Def para criar as viagens"}

@trips_router.get("/editar")
async def editar():
    return {"mensagen" : "Def para editar as viagens"}

@trips_router.get("/time")
async def time():
    return {"mensagen" : "Def para editar horario das viagens"}


