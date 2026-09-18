# companies.py → empresas
from fastapi import APIRouter, Depends, HTTPException
from models import Company, db, User
from sqlalchemy.orm import Session
from dependecies import session_parametr, verificar_token, verificar_admin
from schemas import CompanySchema




companies_router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(verificar_token)])
@companies_router.get("/")
async def companies():
    """"
Essa é a rota padrão de companias do nosso sistema. Todas as companhias precissam passar por aqui
    """
    return{"mensagem": "Você acessou a rota de companhias"}

@companies_router.post("/create")
async def creat_companie(
    companies_schema: CompanySchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr)):
    companies = session.query(Company).filter(Company.name == companies_schema.name).first()
    if companies:
            raise HTTPException(status_code=400, detail="Companhia já cadastrada")

    else:
         new_companie = Company(companies_schema.name, companies_schema.active)
         session.add(new_companie)
         session.commit()
         return {"mensagem": f"Companhia cadastrada com sucesso {companies_schema.name}"}


@companies_router.delete("/{company_id}")
async def delete_companie(
     company_id: int,
     user: User = Depends(verificar_admin),
     session: Session = Depends(session_parametr),):
     companies = session.query(Company).filter(Company.id == company_id).first()
     if not companies:
          raise HTTPException(status_code=404, detail="Companhia não encontrada")
     session.delete(companies)
     session.commit()
     return{"mensagem": f"Companhia {companies.name} excluida com sucesso"}


         