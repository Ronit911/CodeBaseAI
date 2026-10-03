from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.repository import Repository, RepoStatus
from app.services.ingestion_service import IngestionService

router = APIRouter()


class IngestRequest(BaseModel):
    github_url: HttpUrl


class IngestResponse(BaseModel):
    repo_id: str
    status: str
    message: str


@router.post("/ingest", response_model=IngestResponse)
def ingest_repository(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Accept a GitHub URL, create a repo record, and kick off background ingestion.
    """
    url_str = str(body.github_url)

    # Idempotency — don't re-ingest the same repo
    existing = db.query(Repository).filter(Repository.github_url == url_str).first()
    if existing:
        return IngestResponse(
            repo_id=existing.id,
            status=existing.status,
            message="Repository already exists.",
        )

    service = IngestionService(db)
    repo = service.create_repo_record(url_str)
    background_tasks.add_task(service.run_pipeline, repo.id)

    return IngestResponse(
        repo_id=repo.id,
        status=repo.status,
        message="Ingestion started.",
    )
