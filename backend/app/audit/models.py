import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_type: Mapped[str] = mapped_column(String(50))  # e.g., user, system, agent
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    action: Mapped[str] = mapped_column(
        String(100), index=True
    )  # e.g., task.publish, payment.reserve
    resource_type: Mapped[str] = mapped_column(
        String(50)
    )  # e.g., task, wallet, api_key
    resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
