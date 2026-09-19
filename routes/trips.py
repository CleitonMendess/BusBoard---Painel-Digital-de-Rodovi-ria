# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependecies import session_parametr, verificar_token, verificar_admin
from schemas import TripSchema, StatusLogCreateSchema
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

    trip.status = status_normalizado
    session.commit()
    session.refresh(trip)

    return {
        "mensagem": "Status da viagem atualizado com sucesso",
        "trip_id": trip.id,
        "status_atual": trip.status,
    }

@trips_router.get("/list")
async def list_trips(Session = Depends(session_parametr),user: User = Depends(verificar_admin) ):
     if user.role != "adm":
          raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")
     else:
          trips = Session.query(Trip).all()
          return{"Viagens" : trips}

@trips_router.post("/{trip_id}/status_logs")
async def creat_status_log(
    trip_id: int,
    status_log_data: StatusLogCreateSchema,
    session: Session = Depends(session_parametr),
    user: User = Depends(verificar_admin), ):
    trip = session.query(Trip).filter(Trip.id == trip_id).first()   # valida o "pedido"
    if not trip:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")

    status_validos = {...}  # mesma lista que você já usa em trips.py:65
    if status_log_data.new_status not in status_validos:
        raise HTTPException(status_code=400, detail="Status inválido")

    log = StatusLog(                                   # cria o "item"
        trip_id=trip.id,
        old_status=status_log_data.old_status or trip.status,
        new_status=status_log_data.new_status,
        changed_by=status_log_data.changed_by or user.id,
    )
    session.add(log)                                   # salva
    session.commit()
    session.refresh(log)
    return {"mensagem": "Histórico de status registrado", "log": log}