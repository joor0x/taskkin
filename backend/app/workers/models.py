import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude_approx: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude_approx: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    # Store lists as JSON/JSONB
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED
    )
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(AvailabilityStatus), default=AvailabilityStatus.AVAILABLE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user = relationship("User", back_populates="worker_profile")
    assignments = relationship("TaskAssignment", back_populates="worker")
