# destinations.py → destinos
from fastapi import APIRouter, Depends, HTTPException
from schemas import DestinationsSchema
from models import Destination, db
from dependecies import session_parametr
from sqlalchemy.orm import Session


destinations_router = APIRouter(prefix="/destinations", tags=["destinations"])


@destinations_router.get("/")
async def destinations():
    """"
Essa é a rota padrão de destinos do nosso sistema. Todas as cidades e estados são cadastrados aqui

    """
    return{"mensagem": "Você está acessando a rota de destinos"}

@destinations_router.post("/destinations")
async def creat_destinations(destinationsSchema: DestinationsSchema, session: Session = Depends(session_parametr)):
    destination = session.query(Destination).filter(Destination.city == destinationsSchema.city and Destination.state == destinationsSchema.state ).first()
    if destination:
                raise HTTPException(status_code=400, detail="Destino já cadastrado")

    else:    
        new_destinations = Destination(destinationsSchema.city, destinationsSchema.state, destinationsSchema.active)
        session.add(new_destinations)
        session.commit()
        return {"mensagem": f"Destino cadastrado com sucesso {destinationsSchema.city, destinationsSchema.state}"}
                    

    
    