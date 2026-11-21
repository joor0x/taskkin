import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class ReputationEventType(str, enum.Enum):
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"
    TASK_LATE = "task_late"
    WORKER_CANCELLED = "worker_cancelled"
    DISPUTE_RESOLVED = "dispute_resolved"
    REQUESTER_CANCELLED_INCORRECTLY = "requester_cancelled_incorrectly"


class ReputationEvent(Base):
    __tablename__ = "reputation_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[ReputationEventType] = mapped_column(
        SQLEnum(ReputationEventType)
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user = relationship("User")
