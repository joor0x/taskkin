import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class TaskCategory(str, enum.Enum):
    WEBSITE_TESTING = "website_testing"
    CONTENT_REVIEW = "content_review"
    TRANSLATION_REVIEW = "translation_review"
    DATA_VERIFICATION = "data_verification"
    LOCAL_BUSINESS_VERIFICATION = "local_business_verification"
    IMAGE_COLLECTION = "image_collection"
    CUSTOM_SAFE_TASK = "custom_safe_task"


class TaskStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    OPEN = "open"
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class LocationMode(str, enum.Enum):
    REMOTE = "remote"
    PHYSICAL = "physical"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(5000))
    category: Mapped[TaskCategory] = mapped_column(SQLEnum(TaskCategory))
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), default=TaskStatus.DRAFT
    )
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    offered_price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    maximum_budget: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location_mode: Mapped[LocationMode] = mapped_column(
        SQLEnum(LocationMode), default=LocationMode.REMOTE
    )
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_requirements: Mapped[list[dict]] = mapped_column(JSON, default=list)

    safety_risk_level: Mapped[str] = mapped_column(String(50), default="low")
    moderation_status: Mapped[str] = mapped_column(String(50), default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="tasks")
    assignments = relationship(
        "TaskAssignment", back_populates="task", cascade="all, delete-orphan"
    )
