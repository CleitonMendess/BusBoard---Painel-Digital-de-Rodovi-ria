#platforms.py → plataformas
from fastapi import APIRouter, Depends, HTTPException
from schemas import PlatformsSchema
from models import Platform, db, User
from dependecies import session_parametr, verificar_token, verificar_admin
from sqlalchemy.orm import Session

platforms_router = APIRouter(prefix="/platforms", tags=["platforms"], dependencies=[Depends(verificar_token)])

@platforms_router.get("/")
async def plataforms():
    return{"mensagem": "Você está acessando a rota de plataformas dos onibus"}

@platforms_router.post("/create_platforms")
async def create_platforms(platforms_schema: PlatformsSchema,
    session: Session = Depends(session_parametr),
    user: User = Depends(verificar_token)):

    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para criar viagens")
    
    plataforms = session.query(Platform).filter(Platform.number == platforms_schema.number).first()
    if plataforms:
        raise HTTPException(status_code=400, detail="Plataforma já cadastrada")

    else:
        new_platforms = Platform(platforms_schema.number, platforms_schema.active)
        session.add(new_platforms)
        session.commit()
        return {"mensagem": f"Plataforma {platforms_schema.number} cadastrada com sucesso"}
    
@platforms_router.get("/list")
async def list_plataforms(Session = Depends(session_parametr),user: User = Depends(verificar_admin) ):
     if user.role != "adm":
          raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")
     else:
          plataforms = Session.query(Platform).all()
          return{"Plataformas" : plataforms}