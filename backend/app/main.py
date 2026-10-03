from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingest, repos
from app.core.config import settings

app = FastAPI(
    title="CodeBaseAI",
    description="Repository intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(repos.router, prefix="/api", tags=["repos"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
