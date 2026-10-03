import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.session import Base


class RepoStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    INDEXING = "indexing"
    DONE = "done"
    ERROR = "error"


class Repository(Base):
    """Stores metadata for each ingested GitHub repository."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[RepoStatus] = mapped_column(
        Enum(RepoStatus), default=RepoStatus.PENDING
    )
    local_path: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
