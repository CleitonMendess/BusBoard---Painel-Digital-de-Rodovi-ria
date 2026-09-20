# board.py → painel público (não exige login) — dados prontos para a TV
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependecies import session_parametr
from models import Trip


board_router = APIRouter(prefix="/board", tags=["board"])


def formatar_viagem(trip):
    return {
        "trip_id": trip.id,
        "company": trip.company.name if trip.company else None,
        "destination": trip.destination.city if trip.destination else None,
        "platform": trip.platform.number if trip.platform else None,
        "scheduled_time": trip.scheduled_time,
        "estimated_time": trip.estimated_time,
        "status": str(trip.status),
    }


@board_router.get("/departures")
async def departures(session: Session = Depends(session_parametr)):
    trips = (
        session.query(Trip)
        .filter(Trip.trip_direction == "SAIDA")
        .order_by(Trip.scheduled_time)
        .all()
    )
    return {"saidas": [formatar_viagem(t) for t in trips]}


@board_router.get("/arrivals")
async def arrivals(session: Session = Depends(session_parametr)):
    trips = (
        session.query(Trip)
        .filter(Trip.trip_direction == "CHEGADA")
        .order_by(Trip.scheduled_time)
        .all()
    )
    return {"chegadas": [formatar_viagem(t) for t in trips]}


@board_router.get("/active")
async def active(session: Session = Depends(session_parametr)):
    em_andamento = {"EMBARQUE", "NO HORARIO", "ATRASADO", "SAIU"}
    trips = (
        session.query(Trip)
        .filter(Trip.status.in_(em_andamento))
        .order_by(Trip.scheduled_time)
        .all()
    )
    return {"em_andamento": [formatar_viagem(t) for t in trips]}