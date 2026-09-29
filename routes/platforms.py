# platforms.py → plataformas
from fastapi import APIRouter, Depends, HTTPException
from schemas import PlatformsSchema, PlatformUpdateSchema
from models import Platform, Trip, db, User
from dependecies import session_parametr, verificar_token, verificar_admin
from sqlalchemy.orm import Session

platforms_router = APIRouter(prefix="/platforms", tags=["platforms"], dependencies=[Depends(verificar_token)])


@platforms_router.get("/")
def plataforms():
    return {"mensagem": "Você está acessando a rota de plataformas dos onibus"}


@platforms_router.post("/create_platforms")
def create_platforms(
    platforms_schema: PlatformsSchema,
    session: Session = Depends(session_parametr),
    user: User = Depends(verificar_admin),
):
    plataforms = session.query(Platform).filter(Platform.number == platforms_schema.number).first()
    if plataforms:
        raise HTTPException(status_code=400, detail="Plataforma já cadastrada")

    active = True if platforms_schema.active is None else platforms_schema.active
    new_platforms = Platform(platforms_schema.number, active)
    session.add(new_platforms)
    session.commit()
    return {"mensagem": f"Plataforma {platforms_schema.number} cadastrada com sucesso"}


@platforms_router.patch("/{platform_id}")
def update_platform(
    platform_id: int,
    data: PlatformUpdateSchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    """Corrige o número e/ou ativa/desativa a plataforma."""
    platform = session.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Plataforma não encontrada")

    if data.number is not None:
        if data.number < 1:
            raise HTTPException(status_code=400, detail="O número da plataforma deve ser maior que zero")
        repetida = (
            session.query(Platform)
            .filter(Platform.number == data.number, Platform.id != platform_id)
            .first()
        )
        if repetida:
            raise HTTPException(status_code=400, detail="Já existe outra plataforma com esse número")
        platform.number = data.number

    if data.active is not None:
        platform.active = data.active

    session.commit()
    return {"mensagem": f"Plataforma {platform.number} atualizada com sucesso"}


@platforms_router.delete("/{platform_id}")
def delete_platform(
    platform_id: int,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    platform = session.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Plataforma não encontrada")

    em_uso = session.query(Trip).filter(Trip.platform_id == platform_id).count()
    if em_uso:
        raise HTTPException(
            status_code=409,
            detail=f"A plataforma {platform.number} tem {em_uso} viagem(ns) cadastrada(s). "
                   "Desative-a em vez de excluir, ou exclua as viagens antes.",
        )

    numero = platform.number
    session.delete(platform)
    session.commit()
    return {"mensagem": f"Plataforma {numero} excluida com sucesso"}


@platforms_router.get("/list")
def list_plataforms(Session=Depends(session_parametr), user: User = Depends(verificar_admin)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")
    plataforms = Session.query(Platform).all()
    return {"Plataformas": plataforms}