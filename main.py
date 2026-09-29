import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
from models import db, Base
from daily_reset import rodar_reinicio_diario


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES =  int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# De onde o front pode chamar a API. Em desenvolvimento o Vite faz proxy
# (frontend/vite.config.ts) e o front roda em http://localhost:5173.
# Em produção, ponha aqui o endereço real do painel, separado por virgula.
CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origem.strip()
]



@asynccontextmanager
async def lifespan(app: FastAPI):
    # tarefa de fundo que reinicia a grade de viagens uma vez por dia
    tarefa = asyncio.create_task(rodar_reinicio_diario())
    yield
    tarefa.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")
oauth2_schema = OAuth2PasswordBearer(tokenUrl="auth/login-form")


def conferir_banco_migrado():
    """O schema é responsabilidade do Alembic. Se ele não rodou, avisa em vez de
    estourar um 'no such table' no meio de uma requisição."""
    with db.connect() as connection:
        tabelas = {
            linha[0]
            for linha in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    faltando = Base.metadata.tables.keys() - tabelas
    if faltando:
        faltando = ", ".join(sorted(faltando))
        raise RuntimeError(
            f"Falta(m) tabela(s) no banco: {faltando}. "
            "Rode as migrations antes de subir o servidor: alembic upgrade head"
        )


conferir_banco_migrado()

from routes.auth import auth_router
from routes.companies import companies_router
from routes.destinations import destinations_router
from routes.platforms import platforms_router
from routes.trips import trips_router
from routes.board import board_router

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(destinations_router)
app.include_router(platforms_router)
app.include_router(trips_router)
app.include_router(board_router)

@app.get("/") 
def home():
    return {"message": "Welcome to the system the buss!"}