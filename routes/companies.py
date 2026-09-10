# companies.py → empresas
from fastapi import APIRouter, Depends, HTTPException
from models import Company, db
from sqlalchemy.orm import Session
from dependecies import session_parametr
from schemas import CompanySchema




companies_router = APIRouter(prefix="/companies", tags=["companies"])
@companies_router.get("/")
async def companies():
    """"
Essa é a rota padrão de companias do nosso sistema. Todas as rotas dos pedidos precisam de autenticação

    """
    return{"mensagem": "Você acessou a rota de companhias"}

@companies_router.post("/companies")
async def creat_companie(companies_schema: CompanySchema, session: Session = Depends(session_parametr)):
    companies = session.query(Company).filter(Company.name == companies_schema.name).first()
    if companies:
            raise HTTPException(status_code=400, detail="Companhia já cadastrada")

    else:
         new_companie = Company(companies_schema.name, companies_schema.active)
         session.add(new_companie)
         session.commit()
         return {"mensagem": f"Companhia cadastrada com sucesso {companies_schema.name}"}
         