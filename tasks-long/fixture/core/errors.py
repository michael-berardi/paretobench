"""Exception types shared by every package."""


class FreightError(Exception):
    """Base class for errors raised on purpose."""


class ValidationError(FreightError, ValueError):
    """A value or record is not acceptable."""


class NotFound(FreightError, KeyError):
    """A record does not exist."""

    def __str__(self):
        return str(self.args[0]) if self.args else "not found"


class ConflictError(FreightError):
    """A record already exists or changed underneath the caller."""
