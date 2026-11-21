from app.common.exceptions import ConflictException
from app.tasks.models import TaskStatus

ALLOWED_TASK_TRANSITIONS = {
    TaskStatus.DRAFT: {
        TaskStatus.PENDING_MODERATION,
        TaskStatus.CANCELLED,
    },
    TaskStatus.PENDING_MODERATION: {
        TaskStatus.OPEN,
        TaskStatus.REJECTED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.OPEN: {
        TaskStatus.ASSIGNED,
        TaskStatus.CANCELLED,
        TaskStatus.EXPIRED,
    },
    TaskStatus.ASSIGNED: {
        TaskStatus.SUBMITTED,
        TaskStatus.CANCELLED,
        TaskStatus.DISPUTED,
    },
    TaskStatus.SUBMITTED: {
        TaskStatus.APPROVED,
        TaskStatus.REJECTED,
        TaskStatus.DISPUTED,
    },
    TaskStatus.REJECTED: {
        TaskStatus.ASSIGNED,
        TaskStatus.SUBMITTED,
        TaskStatus.DISPUTED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.DISPUTED: {
        TaskStatus.APPROVED,
        TaskStatus.REJECTED,
        TaskStatus.CANCELLED,
    },
}


def validate_task_transition(
    current_status: TaskStatus, new_status: TaskStatus
) -> None:
    """Validate if transition from current_status to new_status is allowed."""
    if current_status == new_status:
        return  # No-op if transition is to the same state

    allowed = ALLOWED_TASK_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ConflictException(
            f"Invalid transition from task state '{current_status.value}' to '{new_status.value}'"
        )
