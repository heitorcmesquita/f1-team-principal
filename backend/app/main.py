from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.race import router as race_router

app = FastAPI(title="F1 Team Principal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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