from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.repository import Repository

router = APIRouter()


@router.get("/repos/{repo_id}")
def get_repo(repo_id: str, db: Session = Depends(get_db)):
    """Return metadata for a single repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {
        "id": repo.id,
        "github_url": repo.github_url,
        "name": repo.name,
        "status": repo.status,
        "created_at": repo.created_at,
    }


@router.get("/repos")
def list_repos(db: Session = Depends(get_db)):
    """List all ingested repositories."""
    repos = db.query(Repository).all()
    return [
        {"id": r.id, "name": r.name, "github_url": r.github_url, "status": r.status}
        for r in repos
    ]
