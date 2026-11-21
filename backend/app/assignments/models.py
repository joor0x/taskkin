import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class AssignmentStatus(str, enum.Enum):
    ACTIVE = "active"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus), default=AssignmentStatus.ACTIVE
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    task = relationship("Task", back_populates="assignments")
    worker = relationship("WorkerProfile", back_populates="assignments")
    submissions = relationship(
        "Submission", back_populates="assignment", cascade="all, delete-orphan"
    )
