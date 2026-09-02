from fastapi import FastAPI 

app = FastAPI() 
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

