from fastapi import FastAPI 

app = FastAPI() 

@app.get("/") 
def home():
    return {"message": "Welcome to the system the buss!"}
