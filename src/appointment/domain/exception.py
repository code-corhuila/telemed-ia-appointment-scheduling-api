"""Typed errors of the appointment-scheduling domain.

The application layer translates these errors to HTTP status codes at the
adapter boundary. The domain itself does not know what an HTTP status is.
"""


class DomainException(Exception):
    """Base class for every domain error."""


class AppointmentNotFound(DomainException):
    """Raised when an appointment cannot be located."""


class InvalidAppointmentTimes(DomainException):
    """Raised when start/end times are inconsistent (end <= start)."""


class AppointmentInThePast(DomainException):
    """Raised when a new appointment is scheduled in the past."""


class InvalidStatusTransition(DomainException):
    """Raised when a status change violates the state machine."""


class SlotUnavailable(DomainException):
    """Raised when the requested time slot conflicts with another appointment."""


class UnauthorizedOperation(DomainException):
    """Raised when the authenticated subject is not allowed to perform the operation."""


class InvalidAvailability(DomainException):
    """Raised when an availability record violates its invariants."""
