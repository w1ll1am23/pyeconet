"""Define package errors."""


class PyeconetError(Exception):
    """A base error."""

    pass


class InvalidCredentialsError(PyeconetError):
    """An error related to invalid requests."""

    pass


class InvalidResponseFormat(PyeconetError):
    """An error related to invalid requests."""

    pass


class GenericHTTPError(PyeconetError):
    """An error related to invalid requests."""

    pass
