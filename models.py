from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_utils.types import ChoiceType

# conexão com o banco de dados
db = create_engine("sqlite:///banco.db")

# base do banco de dados
Base = declarative_base()

# criar as classes/tabelas do banco
# usuarios = id, name, email, password_hash, role, active, created_at
# empresas = id, name, active, created_at
# destinos = id, name, state, active
# plataformas = id, number, active
# viagens = id, type, scheduled_time, estimated_time, status, company_id, destination_id, platform_id, created_at, updated_at


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="operador")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # cpf = Column(String, unique=True, index=True, nullable=False)


    def __init__(self, name, email, password_hash, role="operador", active=True):
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.active = active


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, name, active=True):
        self.name = name
        self.active = active


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    def __init__(self, city, state, active=True):
        self.city = city
        self.state = state
        self.active = active

class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    def __init__(self, number, active=True):
        self.number = number
        self.active = active

class Trip(Base):
    __tablename__ = "trips"

    STATUS_TRIP = (
        ("AGENDADO", "AGENDADO"),
        ("NO HORARIO", "NO HORARIO"),
        ("EMBARQUE", "EMBARQUE"),
        ("ATRASADO", "ATRASADO"),
        ("CANCELADO", "CANCELADO"),
        ("SAIU", "SAIU"),
        ("CHEGOU", "CHEGOU"),
    )
    
    id = Column("id", Integer, primary_key=True, index=True)
    type = Column("type", String, nullable=False)
    scheduled_time = Column("scheduled_time", String, nullable=False)
    estimated_time = Column("estimated_time", String, nullable=True)
    status = Column("status", ChoiceType(choices=STATUS_TRIP), default="AGENDADO")
    created_at = Column("created_at", DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    company_id = Column("company_id", Integer, ForeignKey("companies.id"))
    destination_id = Column("destination_id", Integer, ForeignKey("destinations.id"))
    platform_id = Column("platform_id", Integer, ForeignKey("platforms.id"))
    trip_direction = Column("trip_direction", String, nullable=False)
    company = relationship("Company")
    destination = relationship("Destination")
    platform = relationship("Platform")

    def __init__(
        self,
        type,
        scheduled_time,
        company_id,
        destination_id,
        platform_id,
        trip_direction,
        estimated_time=None,
        status="AGENDADO",
    ):
        self.type = type
        self.scheduled_time = scheduled_time
        self.estimated_time = estimated_time
        self.status = status 
        self.company_id = company_id
        self.destination_id = destination_id
        self.platform_id = platform_id
        self.trip_direction = trip_direction


# executar a criação dos metadados do banco
# Base.metadata.create_all(bind=db)

class StatusLog(Base):                          # (A)
    __tablename__ = "status_logs"               # (B)

    id = Column(Integer, primary_key=True, index=True)                       # (C)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)        # (D)
    old_status = Column(String, nullable=False)                              # (E)
    new_status = Column(String, nullable=False)                              # (E)
    changed_by = Column(Integer, ForeignKey("users.id"))                     # (F)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)   # (G)


class AppState(Base):
    """Pequenos valores do sistema (ex.: qual foi o último dia em que a grade foi reiniciada)."""
    __tablename__ = "app_state"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value