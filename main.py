from fastapi import FastAPI 
from passlib.context import CryptContext
from dotenv import load_dotenv
import os


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI() 

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

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

