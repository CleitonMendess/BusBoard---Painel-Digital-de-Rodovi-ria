# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependecies import session_parametr, verificar_token, verificar_admin
from schemas import TripSchema, StatusLogCreateSchema, Shcema_Time
from models import Trip, Company, Destination,Platform, User, StatusLog


trips_router = APIRouter(prefix="/trips", tags=["trips"], dependencies=[Depends(verificar_token)])

""""
Apenas listar pode ser acessado por um usuario que não é ADM
    """
@trips_router.get("/")
async def viagens():
    return {"mensagen" : "Você está acessando a pagina de viagens"}


@trips_router.post("/create_trips")
async def create_trips(trip_schema: TripSchema,
session: Session = Depends(session_parametr),
user: User = Depends(verificar_token)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para criar viagens")
    
    trip_direction = trip_schema.trip_direction.upper()
    if trip_direction not in {"SAIDA", "CHEGADA"}:
        raise HTTPException(status_code=400, detail="trip_direction deve ser SAIDA ou CHEGADA")

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
        trip_direction=trip_direction,
        estimated_time=trip_schema.estimated_time,
        status=trip_schema.status or "AGENDADO",
    )
    session.add(new_trip)
    session.commit()
    session.refresh(new_trip)
    return {"mensagem": "Viagem cadastrada com sucesso", "trip": new_trip}

@trips_router.patch("/status/{id_trip}")
async def status_trip(id_trip: int, status: str,
session: Session = Depends(session_parametr),
 user: User = Depends(verificar_token)):

    if user.role != "adm":
        raise HTTPException(status_code=401, detail="Você não tem autorização para fazer essa modificação")

    trip = session.query(Trip).filter(Trip.id == id_trip).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")

    status_validos = {
        "AGENDADO",
        "NO HORARIO",
        "EMBARQUE",
        "ATRASADO",
        "CANCELADO",
        "SAIU",
        "CHEGOU",
    }

    status_normalizado = status.upper()
    if status_normalizado not in status_validos:
        raise HTTPException(status_code=400, detail="Status inválido")

    status_anterior = trip.status
    trip.status = status_normalizado
    session.add(StatusLog(trip_id=trip.id,
    old_status=str(status_anterior),   # str() para guardar "AGENDADO" (era um objeto Choice)
    new_status=status_normalizado,
    changed_by=user.id,))
    session.commit()
    session.refresh(trip)

    return {
        "mensagem": "Status da viagem atualizado com sucesso",
        "trip_id": trip.id,
        "status_atual": str(trip.status),
    }

@trips_router.get("/list")
async def list_trips(Session = Depends(session_parametr), user: User = Depends(verificar_admin)):
    trips = Session.query(Trip).all()
    return {"Viagens": [
        {
            "trip_id": t.id,
            "type": t.type,
            "trip_direction": t.trip_direction,
            "company": t.company.name if t.company else None,
            "destination": t.destination.city if t.destination else None,
            "platform": t.platform.number if t.platform else None,
            "scheduled_time": t.scheduled_time,
            "estimated_time": t.estimated_time,
            "status": str(t.status),
        }
        for t in trips
    ]}

@trips_router.patch("/time/{id_trip}")
async def time_trips(
id_trip: int,
time_trip: Shcema_Time,
session: Session = Depends(session_parametr),
user: User = Depends(verificar_token)):

    if user.role not in {"adm", "operador"}:
        raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")

    trip = session.query(Trip).filter(Trip.id == id_trip).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")

    trip.scheduled_time = time_trip.scheduled_time
    if time_trip.estimated_time:
        trip.estimated_time = time_trip.estimated_time


    session.commit()
    session.refresh(trip)

    return {
        "mensagem": "Horário atualizado com sucesso",
        "trip_id": trip.id,
        "scheduled_time": trip.scheduled_time,
        "estimated_time": trip.estimated_time,
    }

@trips_router.delete("/{trip_id}")
async def delete_trip(
     trip_id: int,
     user: User = Depends(verificar_admin),
     session: Session = Depends(session_parametr),):
     trip = session.query(Trip).filter(Trip.id == trip_id).first()
     if not trip:
          raise HTTPException(status_code=404, detail="Viagem não encontrada")
     company_name = trip.company.name if trip.company else "desconhecida"
     session.delete(trip)
     session.commit()
     return{"mensagem": f"Viagem da companhia {company_name} excluida com sucesso"}