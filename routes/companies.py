# companies.py → empresas
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from models import Company, Trip, db, User
from sqlalchemy.orm import Session
from dependecies import session_parametr, verificar_token, verificar_admin
from schemas import CompanySchema, CompanyUpdateSchema


companies_router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(verificar_token)])


@companies_router.get("/")
def companies():
    """
    Essa é a rota padrão de companias do nosso sistema. Todas as companhias precissam passar por aqui
    """
    return {"mensagem": "Você acessou a rota de companhias"}


@companies_router.post("/create")
def create_companie(
    companies_schema: CompanySchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    companies = session.query(Company).filter(Company.name == companies_schema.name).first()
    if companies:
        raise HTTPException(status_code=400, detail="Companhia já cadastrada")

    new_companie = Company(companies_schema.name, companies_schema.active)
    session.add(new_companie)
    session.commit()
    return {"mensagem": f"Companhia cadastrada com sucesso {companies_schema.name}"}


@companies_router.patch("/{company_id}")
def update_companie(
    company_id: int,
    data: CompanyUpdateSchema,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    """Edita o nome e/ou ativa/desativa a empresa."""
    company = session.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Companhia não encontrada")

    if data.name is not None:
        novo_nome = data.name.strip()
        if not novo_nome:
            raise HTTPException(status_code=400, detail="O nome não pode ficar vazio")
        repetida = (
            session.query(Company)
            .filter(func.lower(Company.name) == novo_nome.lower(), Company.id != company_id)
            .first()
        )
        if repetida:
            raise HTTPException(status_code=400, detail="Já existe outra companhia com esse nome")
        company.name = novo_nome

    if data.active is not None:
        company.active = data.active

    session.commit()
    return {"mensagem": f"Companhia {company.name} atualizada com sucesso"}


@companies_router.delete("/{company_id}")
def delete_companie(
    company_id: int,
    user: User = Depends(verificar_admin),
    session: Session = Depends(session_parametr),
):
    companies = session.query(Company).filter(Company.id == company_id).first()
    if not companies:
        raise HTTPException(status_code=404, detail="Companhia não encontrada")

    em_uso = session.query(Trip).filter(Trip.company_id == company_id).count()
    if em_uso:
        raise HTTPException(
            status_code=409,
            detail=f"A companhia {companies.name} tem {em_uso} viagem(ns) cadastrada(s). "
                   "Desative-a em vez de excluir, ou exclua as viagens antes.",
        )

    nome = companies.name
    session.delete(companies)
    session.commit()
    return {"mensagem": f"Companhia {nome} excluida com sucesso"}


@companies_router.get("/list")
def list_companies(Session=Depends(session_parametr), user: User = Depends(verificar_admin)):
    if user.role != "adm":
        raise HTTPException(status_code=403, detail="Você não tem autorização para essa operação")
    companies = Session.query(Company).all()
    return {"Companhias": companies}