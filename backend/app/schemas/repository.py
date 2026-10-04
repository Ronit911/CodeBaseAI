"""
Repository schema — shared representation of an ingested repo.

Used by the API layer and the ingestion service to pass repo
information around without exposing the ORM model directly.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, HttpUrl


class RepositoryStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    INDEXING = "indexing"
    DONE = "done"
    ERROR = "error"


class RepositoryCreate(BaseModel):
    """Input: what the caller supplies to create a new repo record."""
    github_url: HttpUrl


class RepositoryRead(BaseModel):
    """Output: what the API returns about a repo."""
    id: str
    github_url: str
    name: str
    status: RepositoryStatus
    local_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RepositoryStatusUpdate(BaseModel):
    """Used internally to propagate status changes through the pipeline."""
    repo_id: str
    status: RepositoryStatus
    error_message: str | None = None
