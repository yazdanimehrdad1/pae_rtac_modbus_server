"""
Custom application exceptions.

Provides a structured way to handle errors across the application layers.
"""

from typing import Any, Optional, Dict


class AppError(Exception):
    """Base class for all application errors."""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.payload = payload


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""
    pass


class ConflictError(AppError):
    """Raised when an operation conflicts with existing data (e.g., duplicate unique field)."""
    pass


class ValidationError(AppError):
    """Raised when input validation fails in the logic layer."""
    pass


class IntegrityError(AppError):
    """Raised when a database integrity constraint is violated."""
    pass


class InternalError(AppError):
    """Raised for unexpected internal errors."""
    pass
