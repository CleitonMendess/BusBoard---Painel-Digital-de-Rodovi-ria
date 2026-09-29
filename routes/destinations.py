# destinations.py → destinos
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from schemas import DestinationsSchema, DestinationUpdateSchema
from models import Destination, Trip, db, User
from dependecies import session_parametr, verificar_token, verificar_admin
from sqlalchemy.orm import Session


destinations_router = APIRouter(prefix="/destinations", tags=["destinations"], dependencies=[Depends(verificar_token)])


def _destino_repetido(session, city, state, ignorar_id=None):
    query = session.query(Destination).filter(
        func.lower(Destination.city) == city.lower(),
        func.lower(Destination.state) == state.lower(),
    )
    if ignorar_id is not None:
        query = query.filter(Destination.id != ignorar_id)
    return query.first()


@destinations_router.get("/")
def destinations():
    """
    Essa é a rota padrão de destinos do nosso sistema. Todas as cidades e estados são cadastrados aqui
    """
    return {"mensagem": "Você está acessando a rota de destinos"}


@destinations_router.post("/create_destinations")
def create_destinations(
    destinationsSchema: DestinationsSchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    city = destinationsSchema.city.strip()
    state = destinationsSchema.state.strip()
    if _destino_repetido(session, city, state):
        raise HTTPException(status_code=400, detail="Destino já cadastrado")

    active = True if destinationsSchema.active is None else destinationsSchema.active
    new_destinations = Destination(city, state, active)
    session.add(new_destinations)
    session.commit()
    return {"mensagem": f"Destino cadastrado com sucesso {city}/{state}"}


@destinations_router.patch("/{destination_id}")
def update_destination(
    destination_id: int,
    data: DestinationUpdateSchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    """Corrige cidade/estado e/ou ativa/desativa o destino."""
    destination = session.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destino não encontrado")

    nova_cidade = data.city.strip() if data.city is not None else destination.city
    novo_estado = data.state.strip() if data.state is not None else destination.state
    if not nova_cidade or not novo_estado:
        raise HTTPException(status_code=400, detail="Cidade e estado não podem ficar vazios")

    if _destino_repetido(session, nova_cidade, novo_estado, ignorar_id=destination_id):
        raise HTTPException(status_code=400, detail="Já existe outro destino com essa cidade e estado")

    destination.city = nova_cidade
    destination.state = novo_estado
    if data.active is not None:
        destination.active = data.active

    session.commit()
    return {"mensagem": f"Destino {destination.city}/{destination.state} atualizado com sucesso"}


@destinations_router.delete("/{destination_id}")
def delete_destination(
    destination_id: int,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    destination = session.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destino não encontrado")

    em_uso = session.query(Trip).filter(Trip.destination_id == destination_id).count()
    if em_uso:
        raise HTTPException(
            status_code=409,
            detail=f"O destino {destination.city}/{destination.state} tem {em_uso} viagem(ns) cadastrada(s). "
                   "Desative-o em vez de excluir, ou exclua as viagens antes.",
        )

    nome = f"{destination.city}/{destination.state}"
    session.delete(destination)
    session.commit()
    return {"mensagem": f"Destino {nome} excluido com sucesso"}


@destinations_router.get("/list")
def list_destinarions(Session=Depends(session_parametr), user: User = Depends(verificar_admin)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")
    destinations = Session.query(Destination).all()
    return {"Destinos": destinations}