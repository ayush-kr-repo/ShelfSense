from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.api import warehouse, optimize, auth

app = FastAPI(title="ShelfSense API")

# Connecting FastAPI to React server
from fastapi.middleware.cors import CORSMiddleware

origins = ["http://localhost:5173"]
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(warehouse.router)
app.include_router(optimize.router)
app.include_router(auth.router)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}
