import asyncio
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from sqlalchemy import text

from models import db, Base
from daily_reset import rodar_reinicio_diario


load_dotenv()


# ---------- configuração ----------
# Falhar aqui, na hora de subir, é muito melhor do que derrubar uma requisição
# no meio do expediente: config errada é problema de deploy, não de uso.
ALGORITHMS_VALIDOS = {"HS256", "HS384", "HS512"}
NIVEIS_VALIDOS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
erros: dict[str, str] = {}


def _texto(nome: str, padrao: str | None = None) -> str:
    valor = (os.getenv(nome) or "").strip()
    if not valor and padrao is None:
        erros[nome] = "não está definida no .env"
    return valor or (padrao or "")


def _inteiro(nome: str, padrao: int | None = None) -> int:
    valor = (os.getenv(nome) or "").strip()
    if not valor:
        if padrao is None:
            erros[nome] = "não está definida no .env"
            return 0
        return padrao
    try:
        return int(valor)
    except ValueError:
        erros[nome] = f"vale {valor!r}, que não é um número inteiro"
        return padrao or 0


SECRET_KEY = _texto("SECRET_KEY")
ALGORITHM = _texto("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _inteiro("ACCESS_TOKEN_EXPIRE_MINUTES")
LOG_LEVEL = _texto("LOG_LEVEL", "INFO").upper()

if SECRET_KEY and len(SECRET_KEY) < 32:
    erros["SECRET_KEY"] = f"tem só {len(SECRET_KEY)} caracteres; use ao menos 32"
if ALGORITHM not in ALGORITHMS_VALIDOS:
    erros["ALGORITHM"] = f"vale {ALGORITHM!r}; use HS256, HS384 ou HS512"
if "ACCESS_TOKEN_EXPIRE_MINUTES" not in erros and ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    erros["ACCESS_TOKEN_EXPIRE_MINUTES"] = "tem que ser maior que zero"
if LOG_LEVEL not in NIVEIS_VALIDOS:
    erros["LOG_LEVEL"] = f"vale {LOG_LEVEL!r}; use DEBUG, INFO, WARNING, ERROR ou CRITICAL"

if erros:
    detalhes = "\n".join(f"  - {chave}: {motivo}" for chave, motivo in erros.items())
    raise RuntimeError(
        f"Configuração inválida no .env:\n{detalhes}\n\n"
        "Copie o .env.example para .env e ajuste. Para gerar uma chave boa:\n"
        '  python -c "import secrets; print(secrets.token_hex(32))"'
    )


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


# ---------- logging ----------
# Sem isto o log.info do reinício diário é descartado (sem handler, INFO não
# sai) e um erro 500 não deixa rastro nenhum. Vai para o console e para um
# arquivo com rotação, para o backend.log não crescer sem limite.
# LOG_FILE vazio (LOG_FILE=) desliga o arquivo e deixa só o console.
LOG_FILE = os.getenv("LOG_FILE", "backend.log").strip()
log = logging.getLogger("busboard")


def configurar_logging() -> None:
    nivel = getattr(logging, LOG_LEVEL, logging.INFO)
    formato = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    handler_arquivo: logging.Handler | None = None
    if LOG_FILE:
        try:
            handler_arquivo = RotatingFileHandler(
                LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
            )
            handlers.append(handler_arquivo)
        except OSError:
            # sem permissão para o arquivo (ex.: pasta somente leitura):
            # o console ainda serve, então segue em frente
            handler_arquivo = None

    for handler in handlers:
        handler.setFormatter(formato)
    logging.basicConfig(level=nivel, handlers=handlers, force=True)

    # o uvicorn não propaga para o root e monta os próprios handlers, então o
    # arquivo precisa ser pendurado direto nos loggers dele
    if handler_arquivo is not None:
        for nome in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logger_uvicorn = logging.getLogger(nome)
            logger_uvicorn.handlers = [handler_arquivo]
            logger_uvicorn.setLevel(nivel)


configurar_logging()
log.info("BusBoard iniciando (log em %s)", LOG_FILE or "apenas console")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # tarefa de fundo que reinicia a grade de viagens uma vez por dia
    tarefa = asyncio.create_task(rodar_reinicio_diario())
    log.info("Tarefa de reinício diário no ar")
    try:
        yield
    finally:
        tarefa.cancel()
    log.info("BusBoard encerrado")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
def erro_inesperado(request: Request, exc: Exception):
    """Erro não tratado vira 500 com registro completo, em vez de sumir.

    O traceback vai para o log (com método e rota); a resposta ao cliente não
    revela nada de interno.
    """
    log.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente de novo ou avise o responsável."},
    )

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
from routes.invites import invites_router

app.include_router(auth_router)
app.include_router(invites_router)
app.include_router(companies_router)
app.include_router(destinations_router)
app.include_router(platforms_router)
app.include_router(trips_router)
app.include_router(board_router)


@app.get("/health")
def health():
    """Checagem viva para o supervisor. Sem senha de propósito: só diz se está de pé."""
    return {"status": "ok"}


# ---------- front ----------
# Em produção o backend também entrega o painel: um processo só, uma porta só,
# sem depender de nginx. Em desenvolvimento o Vite (frontend/vite.config.ts)
# serve o front e faz proxy da API, então o backend fica só com a API.
#
# O front decide entre painel e TV pelo caminho (/painel é a TV), por isso as
# duas rotas entregam o mesmo index.html e quem faz a escolha é o JavaScript.
class ArquivosEstaticos(StaticFiles):
    """StaticFiles com Cache-Control.

    Os arquivos em /assets têm hash no nome (index-abc123.js), então mudam de
    nome quando mudam de conteúdo: podem ficar cacheados para sempre. Já o
    index.html aponta para esses nomes, então precisa ser revalidado sempre —
    senão um deploy novo continua servindo o index antigo e o navegador nunca
    vê a versão nova.
    """

    def __init__(self, *args, cache_control: str = "public, max-age=0, must-revalidate", **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_control = cache_control

    def file_response(self, *args, **kwargs) -> Response:
        resposta = super().file_response(*args, **kwargs)
        resposta.headers["Cache-Control"] = self.cache_control
        return resposta


def montar_front(app: FastAPI, pasta: Path) -> bool:
    """Serve o frontend compilado. Devolve False se ainda não foi compilado."""
    index = pasta / "index.html"
    if not index.is_file():
        log.warning(
            "Front não encontrado em %s — a API funciona, mas o painel não abre. "
            "Rode `npm run build` em frontend/ (ou defina FRONTEND_DIST).",
            pasta,
        )
        return False

    app.mount(
        "/assets",
        ArquivosEstaticos(
            directory=pasta / "assets",
            cache_control="public, max-age=31536000, immutable",
        ),
        name="assets",
    )

    def painel_admin():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    def painel_tv():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    app.add_api_route("/", painel_admin, methods=["GET"], include_in_schema=False)
    app.add_api_route("/painel", painel_tv, methods=["GET"], include_in_schema=False)
    # /cadastro/<codigo> é o link que o ADM manda para quem vai criar a conta.
    # O código tem um trecho só (o token_urlsafe não usa "/"), então uma rota
    # com um parâmetro resolve.
    app.add_api_route(
        "/cadastro/{token}",
        painel_admin,
        methods=["GET"],
        include_in_schema=False,
    )
    # favicon.svg, icons.svg e qualquer outro arquivo solto do dist
    app.mount(
        "/",
        ArquivosEstaticos(directory=pasta, html=True),
        name="front",
    )
    return True


FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", "").strip() or (Path(__file__).parent / "frontend" / "dist"))
montar_front(app, FRONTEND_DIST)
