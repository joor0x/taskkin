import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_assignments.id", ondelete="CASCADE"), index=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True
    )
    text_result: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    structured_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        SQLEnum(SubmissionStatus), default=SubmissionStatus.PENDING
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationships
    assignment = relationship("TaskAssignment", back_populates="submissions")
    evidence = relationship(
        "Evidence", back_populates="submission", cascade="all, delete-orphan"
    )
