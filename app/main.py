from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import warehouse, optimize, auth

app = FastAPI(title="ShelfSense API")

app.include_router(warehouse.router)
app.include_router(optimize.router)
app.include_router(auth.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}
