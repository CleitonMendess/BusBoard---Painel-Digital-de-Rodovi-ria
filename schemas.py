from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# Schema de usuário
# Serve para receber os dados de cadastro/login do usuário
class UserSchema(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "commom"
    active: Optional[bool] = True

    class Config:
        from_attributes = True

#Companhias
class CompanySchema(BaseModel):
    name: str
    active: Optional[bool] = True

    class Config: 
        from_attributes = True

class DestinationsSchema(BaseModel):
    city: str
    state: str
    active: Optional[bool]

    class Config:
        from_attributes = True

class PlatformsSchema(BaseModel):
    number: int
    active: Optional[bool]

    class Config:
        from_attributes = True

class LoginSchema(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True

class RoleSchema(BaseModel):
    role: str

    class Config:
        from_attributes = True


# Base para qualquer schema de viagem
# Aqui ficam os campos que toda viagem tem em comum
class TripBaseSchema(BaseModel):
    type: str  # tipo da viagem, ex: INTERESTADUAL, LOCAL, etc.
    scheduled_time: str  # horário agendado da viagem
    estimated_time: Optional[str] = None  # tempo estimado de chegada
    status: Optional[str] = "AGENDADO"  # status inicial da viagem
    company_id: int  # empresa relacionada
    destination_id: int  # destino da viagem
    platform_id: int  # plataforma da rodoviária

    class Config:
        from_attributes = True


# Schema principal para criar uma viagem
class TripSchema(BaseModel):
    type: str
    scheduled_time: str
    estimated_time: Optional[str] = None
    status: Optional[str] = None
    company_id: Optional[int] = None
    destination_id: Optional[int] = None
    platform_id: Optional[int] = None

    class Config:
        from_attributes = True


# Schema usado para responder a viagem ao cliente
# Aqui inclui os dados que vêm do banco, como id e datas de criação/atualização
class TripResponseSchema(TripBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StatusLogCreateSchema(BaseModel):
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None   # se não mandar, usa o user logado

    class Config:
        from_attributes = True