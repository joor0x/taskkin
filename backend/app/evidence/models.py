import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class EvidenceType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    URL = "url"
    TEXT = "text"
    JSON = "json"


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(SQLEnum(EvidenceType))
    storage_key: Mapped[str] = mapped_column(String(512))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(
        JSON, default=dict
    )  # Rename metadata to avoid SQLAlchemy metadata collision
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    submission = relationship("Submission", back_populates="evidence")
