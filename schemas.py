from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# Schema de usuário
# Serve para receber os dados de cadastro/login do usuário
class UserSchema(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "operador"
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

#Ativar ou desativar um usuário
class ActiveSchema(BaseModel):
    active: bool

    class Config:
        from_attributes = True

#Renovar a sessão: manda o refresh_token recebido no login
class RefreshSchema(BaseModel):
    refresh_token: str

    class Config:
        from_attributes = True


# ---------- Convites de cadastro ----------

class InviteCreateSchema(BaseModel):
    role: Optional[str] = "operador"
    # em horas; se não vier, vale o padrão do .env
    validade_horas: Optional[int] = None

    class Config:
        from_attributes = True


class InviteSchema(BaseModel):
    id: int
    role: str
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
    usado_por: Optional[str] = None
    situacao: str

    class Config:
        from_attributes = True


# Checagem do código: o front pergunta antes de mostrar o formulário
class InviteCheckSchema(BaseModel):
    valido: bool
    role: Optional[str] = None
    motivo: Optional[str] = None


class RegisterSchema(BaseModel):
    """Cadastro feito por quem recebeu o convite."""
    token: str
    name: str
    email: str
    password: str

    class Config:
        from_attributes = True


# Base para qualquer schema de viagem
# Aqui ficam os campos que toda viagem tem em comum
class TripBaseSchema(BaseModel):
    type: str  # tipo da viagem, ex: INTERESTADUAL, LOCAL, etc.
    trip_direction: str  # SAIDA ou CHEGADA
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
    trip_direction: str
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

class Shcema_Time(BaseModel):
    scheduled_time: str
    estimated_time: Optional[str] = None
    class Config:
        from_attributes = True


# ---- Schemas de edição parcial (só muda o que for enviado) ----
class CompanyUpdateSchema(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class DestinationUpdateSchema(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    active: Optional[bool] = None


class PlatformUpdateSchema(BaseModel):
    number: Optional[int] = None
    active: Optional[bool] = None


class TripUpdateSchema(BaseModel):
    type: Optional[str] = None
    trip_direction: Optional[str] = None
    scheduled_time: Optional[str] = None
    estimated_time: Optional[str] = None  # "" limpa a previsão
    status: Optional[str] = None
    company_id: Optional[int] = None
    destination_id: Optional[int] = None
    platform_id: Optional[int] = None