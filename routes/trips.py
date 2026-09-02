# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter

trips_router = APIRouter(prefix="/trips", tags=["trips"])