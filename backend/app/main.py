from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.assignments import router as assignments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.payments import router as payments_router
from app.api.v1.pricing import router as pricing_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.workers import router as workers_router
from app.assignments.models import TaskAssignment  # noqa: F401
from app.audit.models import AuditEvent  # noqa: F401

# Import all models to register them with SQLAlchemy
from app.auth.models import RefreshToken, User  # noqa: F401
from app.common.models import IdempotencyKey  # noqa: F401
from app.config import settings
from app.evidence.models import Evidence  # noqa: F401
from app.organizations.models import (  # noqa: F401
    APIKey,
    Organization,
    OrganizationMember,
)
from app.payments.models import LedgerEntry, Wallet  # noqa: F401
from app.reputation.models import ReputationEvent  # noqa: F401
from app.submissions.models import Submission  # noqa: F401
from app.tasks.models import Task  # noqa: F401
from app.webhooks.models import WebhookDelivery, WebhookEndpoint  # noqa: F401
from app.workers.models import WorkerProfile  # noqa: F401

app = FastAPI(
    title="TaskKin API",
    description="MVP API for TaskKin platform",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(workers_router, prefix="/api/v1")
app.include_router(pricing_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(assignments_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(submissions_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/ready")
async def ready_check():
    # In the future, we can check DB and Redis connection health here.
    return {"status": "ready"}
