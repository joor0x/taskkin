import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_organization_idempotency_key"
        ),
    )

    # We use a composite index or primary key. Let's use a UUID primary key,
    # but make (organization_id, idempotency_key) unique.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), index=True)
    request_hash: Mapped[str] = mapped_column(
        String(64)
    )  # SHA-256 hash of the request body
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[str] = mapped_column(
        String
    )  # Store JSON response body as string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
