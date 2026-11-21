class TaskKinException(Exception):
    """Base exception for TaskKin."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundException(TaskKinException):
    """Resource not found."""

    pass


class UnauthorizedException(TaskKinException):
    """Unauthorized access."""

    pass


class ForbiddenException(TaskKinException):
    """Forbidden action."""

    pass


class ConflictException(TaskKinException):
    """Resource conflict (e.g., duplicate, state conflict, concurrency issue)."""

    pass


class BadRequestException(TaskKinException):
    """Invalid input or bad request."""

    pass
