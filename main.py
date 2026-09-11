from fastapi import FastAPI 
from sqlalchemy import text
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
from models import db, Base


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 

app = FastAPI() 

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

Base.metadata.create_all(bind=db)


with db.connect() as connection:
    columns = {
        row[1]
        for row in connection.execute(text("PRAGMA table_info(users)"))
    }
    if "users" in {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}:
        if "email" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR"))
            if "username" in columns:
                connection.execute(text("UPDATE users SET email = username WHERE email IS NULL"))
            connection.commit()

from routes.auth import auth_router
from routes.companies import companies_router
from routes.destinations import destinations_router
from routes.platforms import platforms_router
from routes.trips import trips_router

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(destinations_router)
app.include_router(platforms_router)
app.include_router(trips_router)

@app.get("/") 
def home():
    return {"message": "Welcome to the system the buss!"}

