# trips.py → viagens, saídas, chegadas, alteração de horário
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependecies import session_parametr, verificar_token, verificar_admin
from schemas import TripSchema, StatusLogCreateSchema, Shcema_Time, TripUpdateSchema
from models import Trip, Company, Destination,Platform, User, StatusLog
from daily_reset import reiniciar_viagens
from daily_reset import viagens_para_confirmar as viagens_para_confirmar_lista


trips_router = APIRouter(prefix="/trips", tags=["trips"], dependencies=[Depends(verificar_token)])

""""
Apenas listar pode ser acessado por um usuario que não é ADM
    """
@trips_router.get("/")
def viagens():
    return {"mensagen" : "Você está acessando a pagina de viagens"}


@trips_router.post("/create_trips")
def create_trips(trip_schema: TripSchema,
session: Session = Depends(session_parametr),
user: User = Depends(verificar_token)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para criar viagens")
    
    trip_direction = trip_schema.trip_direction.upper()
    if trip_direction not in {"SAIDA", "CHEGADA"}:
        raise HTTPException(status_code=400, detail="trip_direction deve ser SAIDA ou CHEGADA")

    tipo = trip_schema.type.upper()
    tipos_validos = {"INTERESTADUAL", "ESTADUAL", "LOCAL", "INTERMUNICIPAL", "METROPOLITANO"}
    if tipo not in tipos_validos:
        raise HTTPException(status_code=400, detail="Tipo de viagem inválido")

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
def status_trip(id_trip: int, status: str,
session: Session = Depends(session_parametr),
 user: User = Depends(verificar_token)):

    if user.role not in {"adm", "operador"}:
        raise HTTPException(status_code=403, detail="Você não tem autorização para fazer essa modificação")

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

@trips_router.get("/pendentes-confirmacao")
def viagens_para_confirmar(
    Session = Depends(session_parametr), user: User = Depends(verificar_admin)
):
    """Viagens cujo horário ou previsão já passou e que ninguém confirmou se o ônibus chegou.

    Só envia, para o operador e o administrador receberem o aviso. Marcar atraso
    é decisão de quem opera: a resposta "não chegou" é o que vira ATRASADO.
    """
    pendentes = viagens_para_confirmar_lista(Session)
    return {
        "total": len(pendentes),
        "viagens": [
            {
                "trip_id": v.id,
                "destination": v.destination.city if v.destination else "",
                "company": v.company.name if v.company else "",
                "scheduled_time": v.scheduled_time,
                "estimated_time": v.estimated_time,
                "status": str(v.status),
                "trip_direction": v.trip_direction,
            }
            for v in pendentes
        ],
    }


@trips_router.get("/list")
def list_trips(Session = Depends(session_parametr), user: User = Depends(verificar_admin)):
    trips = Session.query(Trip).all()
    return {"Viagens": [
        {
            "trip_id": t.id,
            "type": t.type,
            "trip_direction": t.trip_direction,
            "company": t.company.name if t.company else None,
            "destination": t.destination.city if t.destination else None,
            "platform": t.platform.number if t.platform else None,
            "company_id": t.company_id,
            "destination_id": t.destination_id,
            "platform_id": t.platform_id,
            "scheduled_time": t.scheduled_time,
            "estimated_time": t.estimated_time,
            "status": str(t.status),
        }
        for t in trips
    ]}

@trips_router.patch("/time/{id_trip}")
def time_trips(
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
    # se a previsão veio no corpo (mesmo vazia), atualiza; vazia = tira a previsão
    if "estimated_time" in time_trip.model_fields_set:
        trip.estimated_time = time_trip.estimated_time or None


    session.commit()
    session.refresh(trip)

    return {
        "mensagem": "Horário atualizado com sucesso",
        "trip_id": trip.id,
        "scheduled_time": trip.scheduled_time,
        "estimated_time": trip.estimated_time,
    }

@trips_router.post("/reset-day")
def reset_day(
    session: Session = Depends(session_parametr),
    user: User = Depends(verificar_admin),
):
    """Reinício manual: todas as viagens voltam para AGENDADO e sem previsão."""
    total = reiniciar_viagens(session)
    return {"mensagem": f"Dia reiniciado: {total} viagem(ns) voltaram para AGENDADO", "total": total}


@trips_router.patch("/{trip_id}")
def update_trip(
    trip_id: int,
    data: TripUpdateSchema,
    session: Session = Depends(session_parametr),
    user: User = Depends(verificar_admin),
):
    """Edita qualquer campo da viagem (só o que for enviado é alterado)."""
    trip = session.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")

    campos = data.model_dump(exclude_unset=True)

    if "trip_direction" in campos:
        direcao = (campos["trip_direction"] or "").upper()
        if direcao not in {"SAIDA", "CHEGADA"}:
            raise HTTPException(status_code=400, detail="trip_direction deve ser SAIDA ou CHEGADA")
        trip.trip_direction = direcao

    if "company_id" in campos:
        if not session.query(Company).filter(Company.id == campos["company_id"]).first():
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        trip.company_id = campos["company_id"]

    if "destination_id" in campos:
        if not session.query(Destination).filter(Destination.id == campos["destination_id"]).first():
            raise HTTPException(status_code=404, detail="Destino não encontrado")
        trip.destination_id = campos["destination_id"]

    if "platform_id" in campos:
        if not session.query(Platform).filter(Platform.id == campos["platform_id"]).first():
            raise HTTPException(status_code=404, detail="Plataforma não encontrada")
        trip.platform_id = campos["platform_id"]

    if "type" in campos and campos["type"]:
        tipo = campos["type"].upper()
        tipos_validos = {"INTERESTADUAL", "ESTADUAL", "LOCAL", "INTERMUNICIPAL", "METROPOLITANO"}
        if tipo not in tipos_validos:
            raise HTTPException(status_code=400, detail="Tipo de viagem inválido")
        trip.type = tipo

    if "scheduled_time" in campos and campos["scheduled_time"]:
        trip.scheduled_time = campos["scheduled_time"]

    if "estimated_time" in campos:
        # string vazia ou null = tirar a previsão
        trip.estimated_time = campos["estimated_time"] or None

    if "status" in campos and campos["status"]:
        novo_status = campos["status"].upper()
        status_validos = {"AGENDADO", "NO HORARIO", "EMBARQUE", "ATRASADO", "CANCELADO", "SAIU", "CHEGOU"}
        if novo_status not in status_validos:
            raise HTTPException(status_code=400, detail="Status inválido")
        status_anterior = str(trip.status)
        if novo_status != status_anterior:
            trip.status = novo_status
            session.add(StatusLog(
                trip_id=trip.id,
                old_status=status_anterior,
                new_status=novo_status,
                changed_by=user.id,
            ))

    session.commit()
    return {"mensagem": "Viagem atualizada com sucesso", "trip_id": trip.id}


@trips_router.delete("/{trip_id}")
def delete_trip(
     trip_id: int,
     user: User = Depends(verificar_admin),
     session: Session = Depends(session_parametr),):
     trip = session.query(Trip).filter(Trip.id == trip_id).first()
     if not trip:
          raise HTTPException(status_code=404, detail="Viagem não encontrada")
     company_name = trip.company.name if trip.company else "desconhecida"
     session.query(StatusLog).filter(StatusLog.trip_id == trip.id).delete()
     session.delete(trip)
     session.commit()
     return{"mensagem": f"Viagem da companhia {company_name} excluida com sucesso"}