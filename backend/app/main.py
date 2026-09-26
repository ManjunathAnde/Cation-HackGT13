from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

# Load backend/.env (one level above this app/ package).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Cation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"ok": True}]})

    ok: bool


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True)
