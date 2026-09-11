# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependecies import session_parametr
from schemas import TripSchema
from models import Trip, Company, Destination,Platform


trips_router = APIRouter(prefix="/trips", tags=["trips"])

""""
Apenas listar pode ser acessado por um usuario que não é ADM
    """
@trips_router.get("/")
async def viagens():
    return {"mensagen" : "Você está acessando a pagina de viagens"}


@trips_router.post("/creat_trips")
async def creat_trips(trip_schema: TripSchema, session: Session = Depends(session_parametr)):
    company = session.query(Company).filter(Company.id == trip_schema.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    destination = session.query(Destination).filter(Destination.id == trip_schema.destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destino não encontrado")

    platform = session.query(Platform).filter(Platform.id == trip_schema.platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Plataforma não encontrada")

    new_trip = Trip(
        type=trip_schema.type,
        scheduled_time=trip_schema.scheduled_time,
        company_id=trip_schema.company_id,
        destination_id=trip_schema.destination_id,
        platform_id=trip_schema.platform_id,
        estimated_time=trip_schema.estimated_time,
        status=trip_schema.status or "AGENDADO",
    )
    session.add(new_trip)
    session.commit()
    session.refresh(new_trip)
    return {"mensagem": "Viagem cadastrada com sucesso", "trip": new_trip}