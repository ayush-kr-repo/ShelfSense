from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import warehouse, optimize, auth

app = FastAPI(title="ShelfSense API")

# Connecting FastAPI to React server
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ShelfSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],       # React dev server
    allow_credentials=True,
    allow_methods=["*"],                            # GET, POST ..
    allow_headers=["*"],                            # including Authoriztion
)

app.include_router(warehouse.router)
app.include_router(optimize.router)
app.include_router(auth.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}
