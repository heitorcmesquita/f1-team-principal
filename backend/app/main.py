from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.race import router as race_router

app = FastAPI(title="F1 Team Principal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(race_router)


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "f1-team-principal"
    }